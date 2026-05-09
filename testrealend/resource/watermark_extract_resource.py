from flask import request, current_app
from flask_restful import Resource
from flask_jwt_extended import jwt_required
from model.Application import Application
from extension.extension import db
from datetime import datetime, timezone
import os
import base64
import hmac
import hashlib
import io
import json
import zipfile
import numpy as np
import logging
from PIL import Image
from werkzeug.utils import secure_filename
from utils.user_limiter import normal_limit
from resource.watermark_utils import (
    safe_extract_zip, QR_SECRET_KEY, decode_qr_from_image,
    parse_qr_text, build_qr_text, get_qr_version
)
from algorithm.extract import extract as vector_extract
from algorithm.raster_reversible_watermark import decode_reversible, recover_reversible
from algorithm.raster_dwt_watermark import extract_dwt, recover_dwt
from algorithm.raster_histogram_watermark import extract_histogram, recover_histogram
from algorithm.quality_metrics import compute_nc


class VectorExtractResource(Resource):
    @jwt_required()
    @normal_limit
    def post(self):
        app_id = request.form.get('application_id')
        if not app_id:
            return {'status': False, 'msg': '缺少申请编号'}, 400

        if 'file' not in request.files:
            return {'status': False, 'msg': '没有上传文件'}, 400

        file = request.files['file']
        if file.filename == '':
            return {'status': False, 'msg': '没有选择文件'}, 400

        item = db.session.get(Application, app_id)
        if not item:
            return {'status': False, 'msg': '未找到对应的申请记录'}, 404

        temp_dir = None
        try:
            data_type = (item.data_type or 'vector').lower()
            filename = secure_filename(file.filename)
            temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp', f'extract_{app_id}')
            os.makedirs(temp_dir, exist_ok=True)
            save_path = os.path.join(temp_dir, filename)
            file.save(save_path)

            if data_type == 'raster':
                return self._extract_raster(item, save_path, temp_dir)
            else:
                return self._extract_vector(item, save_path, temp_dir)

        except Exception as e:
            logging.error(str(e))
            return {'status': False, 'msg': '操作失败，请稍后重试'}, 500
        finally:
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

    def _extract_vector(self, item, zip_path, temp_dir):
        if not item.vr_data:
            return {'status': False, 'msg': '未找到原始特征数据'}, 404

        extract_dir = os.path.join(temp_dir, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            safe_extract_zip(zip_ref, extract_dir)

        shp_file = None
        for root, _, files in os.walk(extract_dir):
            for f in files:
                if f.endswith('.shp'):
                    shp_file = os.path.join(root, f)
                    break
            if shp_file:
                break

        if not shp_file:
            return {'status': False, 'msg': 'ZIP包中未找到 .shp 文件'}, 400

        vr = json.loads(item.vr_data)
        _, watermark_img_path = vector_extract(shp_file, vr)

        with open(watermark_img_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()

        return self._build_response(item, watermark_img_path, encoded_string, 'Vector')

    def _extract_raster(self, item, file_path, temp_dir):
        import shutil

        # Find the metadata files alongside the stego image
        wm_meta_path = getattr(item, 'watermark_path_meta', None)
        wm_map_path = getattr(item, 'watermark_path_map', None)

        # Try to find metadata from the stego output directory
        stego_dir = os.path.dirname(item.watermark_path) if item.watermark_path else ''
        if not wm_meta_path and stego_dir:
            candidates = [f for f in os.listdir(stego_dir) if f.endswith('_wm_meta.json')]
            wm_meta_path = os.path.join(stego_dir, candidates[0]) if candidates else None
        if not wm_map_path and stego_dir:
            candidates = [f for f in os.listdir(stego_dir) if f.endswith('_wm_map.npz')]
            wm_map_path = os.path.join(stego_dir, candidates[0]) if candidates else None

        if not wm_meta_path or not os.path.exists(wm_meta_path):
            return {'status': False, 'msg': '未找到栅格水印元数据，无法提取'}, 400

        # Detect algorithm from metadata
        algo = 'lsb'
        try:
            with open(wm_meta_path, 'r', encoding='utf-8') as fp:
                meta_data = json.load(fp)
            algo = meta_data.get('algorithm', 'lsb')
        except Exception:
            pass

        output_path = os.path.join(temp_dir, 'decoded_watermark.png')
        if algo == 'dwt':
            extract_dwt(file_path, wm_meta_path, output_path)
        elif algo == 'histogram_shifting':
            extract_histogram(file_path, wm_meta_path, output_path)
        else:
            decode_reversible(file_path, wm_meta_path, output_path)

        if not os.path.exists(output_path):
            return {'status': False, 'msg': '栅格水印提取失败'}, 500

        # Also recover the original image
        recovered_path = None
        try:
            recovered_path = os.path.join(temp_dir, 'recovered_original.png')
            if algo == 'dwt':
                recover_dwt(file_path, wm_meta_path, recovered_path)
            elif algo == 'histogram_shifting':
                recover_histogram(file_path, wm_meta_path, recovered_path)
            elif wm_map_path and os.path.exists(wm_map_path):
                from algorithm.raster_reversible_watermark import recover_reversible
                recover_reversible(file_path, wm_map_path, wm_meta_path, recovered_path)
            else:
                recovered_path = None
        except Exception as e:
            logging.warning('Original image recovery failed: %s', e)
            recovered_path = None

        with open(output_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()

        response_dict, status_code = self._build_response(item, output_path, encoded_string, 'Raster')

        # Add recovered original image to response if available
        if recovered_path and os.path.exists(recovered_path):
            with open(recovered_path, "rb") as f:
                response_dict['recovered_base64'] = base64.b64encode(f.read()).decode()
            response_dict['data']['decoded_info']['verify']['recovered'] = True
        else:
            response_dict['data']['decoded_info']['verify']['recovered'] = False

        return response_dict, status_code

    def _build_response(self, item, watermark_img_path, encoded_string, data_type):
        qr_text = decode_qr_from_image(watermark_img_path)
        verify_ok = qr_text is not None
        parsed = parse_qr_text(qr_text) if qr_text else {}

        # HMAC signature verification
        signature_ok = False
        if verify_ok and QR_SECRET_KEY and 'Signature' in parsed:
            try:
                lines = qr_text.split('\n')
                sig_idx = next((i for i, l in enumerate(lines) if l.startswith('Signature:')), None)
                if sig_idx is not None:
                    claimed_sig = lines[sig_idx].split(':', 1)[1].strip()
                    content_to_verify = "\n".join(lines[:sig_idx])
                    expected_sig = hmac.new(
                        QR_SECRET_KEY.encode(),
                        content_to_verify.encode(),
                        hashlib.sha256
                    ).hexdigest()[:16]
                    signature_ok = hmac.compare_digest(claimed_sig, expected_sig)
            except Exception:
                signature_ok = False

        # Compute quality metrics for vector extraction
        nc_value = None
        if data_type == 'Vector' and item.qrcode and verify_ok:
            try:
                original_qr_img = Image.open(io.BytesIO(base64.b64decode(item.qrcode))).convert('L')
                extracted_qr_img = Image.open(watermark_img_path).convert('L')
                orig_bits = (np.array(original_qr_img) > 127).astype(int).flatten()
                extr_bits = (np.array(extracted_qr_img) > 127).astype(int).flatten()
                nc_value = compute_nc(orig_bits, extr_bits)
            except Exception:
                pass

        return {
            'status': True,
            'watermark_base64': encoded_string,
            'data': {
                'decoded_info': {
                    'verify': {
                        'digest_ok': verify_ok,
                        'signature_ok': signature_ok,
                        'nc_value': round(nc_value, 6) if nc_value is not None else None,
                        'message': '二维码校验成功' if verify_ok else '二维码解码失败'
                    },
                    'normalized': {
                        'id': item.id,
                        'application_number': f"APP-{item.id:04d}",
                        'application_status': 'Approved',
                        'data_type': data_type,
                        'applicant': item.applicant_name,
                        'applicant_id': item.applicant_user_number,
                        'approver_1': item.adm1_name or parsed.get('Admin1', 'Admin1'),
                        'approver_2': item.adm2_name or parsed.get('Admin2', 'Admin2'),
                        'submitted_at': item.application_submission_time.strftime('%Y-%m-%d %H:%M:%S') if item.application_submission_time else None,
                        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                        'reason': item.reason,
                        '_qr_raw': qr_text
                    },
                    'parsed': parsed
                }
            }
        }, 200


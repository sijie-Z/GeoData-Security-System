from flask import request, send_file, current_app
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from model.Application import Application
from extension.extension import db
from datetime import datetime
import os
import base64
import qrcode
import io
import json
import zipfile
import numpy as np
import logging
import hmac
from utils.metrics import record_watermark
import hashlib
from PIL import Image
from model.Shp_Data import Shp
from model.Raster_Data import RasterData
from model.watermark_verification import WatermarkVerification
from algorithm.embed import embed as vector_embed
from algorithm.extract import extract as vector_extract
from algorithm.raster_reversible_watermark import embed_reversible, decode_reversible
from algorithm.raster_dwt_watermark import embed_dwt, extract_dwt, recover_dwt
from algorithm.raster_histogram_watermark import embed_histogram, extract_histogram, recover_histogram
from algorithm.quality_metrics import compute_nc, compute_psnr, compute_ssim_simple, compute_ber
from werkzeug.utils import secure_filename
from utils.log_helper import log_action
from utils.required import admin_required
from utils.user_limiter import normal_limit, relaxed_limit


def _safe_extract_zip(zip_ref, extract_dir):
    """安全解压ZIP，防止路径穿越攻击"""
    for member in zip_ref.namelist():
        target = os.path.realpath(os.path.join(extract_dir, member))
        if not target.startswith(os.path.realpath(extract_dir)):
            raise ValueError(f"非法文件路径: {member}")
    zip_ref.extractall(extract_dir)

# Secret key for QR signature
QR_SECRET_KEY = os.environ.get('QR_SECRET_KEY')
if not QR_SECRET_KEY:
    import logging as _logging
    _logging.warning("QR_SECRET_KEY not set — QR signatures will be insecure. Set this env var in production.")
    # Use a dev-only fallback so the app doesn't crash on .encode()
    QR_SECRET_KEY = 'dev-only-qr-key-replace-in-production'


def _decode_qr_from_image(image_path):
    """Decode QR code from image file. Returns decoded text or None."""
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
        decoded_objects = pyzbar_decode(Image.open(image_path))
        if decoded_objects:
            return decoded_objects[0].data.decode('utf-8')
    except Exception:
        pass
    try:
        import cv2
        img = cv2.imread(image_path)
        if img is not None:
            detector = cv2.QRCodeDetector()
            decoded, _, _ = detector.detectAndDecode(img)
            if decoded:
                return decoded
    except Exception:
        pass
    return None


def _parse_qr_text(qr_text):
    """Parse QR text into structured data dict."""
    result = {'_raw': qr_text}
    for line in qr_text.split('\n'):
        if ':' in line:
            key, _, value = line.partition(':')
            result[key.strip()] = value.strip()
    return result

def _build_qr_text(item, payload):
    """Build QR code content with all metadata and signature"""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    # Build content lines
    lines = [
        f"=== SPATIAL DATA TRACKING SYSTEM ===",
        f"AppID: {item.id}",
        f"Data: {item.data_alias}",
        f"DataID: {item.data_id}",
        f"DataType: {item.data_type or 'vector'}",
        f"Applicant: {item.applicant_name}",
        f"ApplicantID: {item.applicant_user_number}",
        f"Time: {timestamp}",
    ]

    # Add optional fields
    optional_fields = ['purpose', 'usage_scope', 'security_level', 'custom_tag', 'reason']
    for key in optional_fields:
        value = payload.get(key)
        if value and str(value).strip():
            lines.append(f"{key.replace('_', ' ').title()}: {str(value).strip()}")

    # Generate signature
    content_to_sign = "\n".join(lines)
    signature = hmac.new(
        QR_SECRET_KEY.encode(),
        content_to_sign.encode(),
        hashlib.sha256
    ).hexdigest()[:16]  # First 16 chars of signature

    lines.append(f"Signature: {signature}")
    lines.append(f"=== END ===")

    return "\n".join(lines), signature


def _get_qr_version(content_length):
    """Auto-detect QR version based on content length"""
    # QR version capacity table for alphanumeric encoding with error correction L
    version_capacities = [
        25, 47, 77, 114, 154, 195, 224, 279, 335, 395,  # v1-v10
        468, 535, 619, 667, 758, 854, 938, 1046, 1153, 1249,  # v11-v20
        1358, 1468, 1588, 1704, 1863, 2020, 2121, 2303, 2431, 2563  # v21-v30
    ]
    for i, capacity in enumerate(version_capacities):
        if content_length <= capacity:
            return i + 1
    return 10  # Default to version 10 if very long


class Adm1GetGenerateWatermarkApplications(Resource):
    @jwt_required()
    def get(self):
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        
        # Only get applications where adm1 has approved
        query = Application.query.filter(Application.adm1_statu == True)
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        
        items = [item.to_dict() for item in pagination.items]
        
        return {
            'status': True,
            'application_data': items,
            'pages': {'total': pagination.total}
        }, 200

class GenerateWatermarkResource(Resource):
    """
    生成水印二维码
    ---
    tags: [Watermark]
    security: [Bearer: []]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [application_id]
          properties:
            application_id: {type: integer, description: 申请编号}
            purpose: {type: string, description: 用途}
            usage_scope: {type: string, description: 使用范围}
            security_level: {type: string, description: 安全级别}
            custom_tag: {type: string, description: 自定义标签}
            reason: {type: string, description: 原因}
    responses:
      200: {description: 水印生成成功}
      404: {description: 申请不存在}
    """
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        app_id = data.get('application_id')

        item = Application.query.get(app_id)
        if not item:
            return {'status': False, 'msg': '申请不存在'}, 404

        try:
            # Build QR content with signature
            qr_content, signature = _build_qr_text(item, data)

            # Auto-detect QR version based on content length
            qr_version = _get_qr_version(len(qr_content))

            # Generate QR code
            qr = qrcode.QRCode(
                version=qr_version,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_content)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            # Save all metadata to database
            item.qrcode = img_str
            item.watermark_generated = True
            item.qr_version = qr_version
            item.qr_signature = signature
            item.generation_timestamp = datetime.utcnow()

            # Save optional fields
            for field in ['purpose', 'usage_scope', 'security_level', 'custom_tag']:
                if data.get(field):
                    setattr(item, field, str(data.get(field)).strip())

            if data.get('reason'):
                item.reason = str(data.get('reason')).strip()

            db.session.commit()

            log_action(
                item.applicant_user_number, item.applicant_name,
                '水印生成', '成功',
                f"app_id={item.id} data_alias={item.data_alias} qr_version={qr_version}"
            )
            record_watermark(data_type=item.data_type or 'vector')

            return {
                'status': True,
                'msg': '水印生成成功',
                'qrcode': img_str,
                'qr_text': qr_content,
                'qr_version': qr_version,
                'signature': signature
            }, 200
        except Exception as e:
            logging.error(str(e))
            return {'status': False, 'msg': '操作失败，请稍后重试'}, 500

class Adm2GetEmbeddingWatermarkApplications(Resource):
    @jwt_required()
    def get(self):
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        data_type = request.args.get('data_type', 'vector').lower()
        
        # adm1 passed AND adm2 passed AND watermark generated
        query = Application.query.filter(
            Application.adm1_statu == True, 
            Application.adm2_statu == True,
            Application.watermark_generated == True
        )
        
        if data_type:
            query = query.filter(Application.data_type == data_type)
            
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        
        items = [item.to_dict() for item in pagination.items]
        
        return {
            'status': True,
            'application_data': items,
            'pages': {'total': pagination.total}
        }, 200

class EmbeddingWatermarkResource(Resource):
    """
    嵌入水印到数据文件
    ---
    tags: [Watermark]
    security: [Bearer: []]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [application_id]
          properties:
            application_id: {type: integer, description: 申请编号}
    responses:
      200: {description: 水印嵌入成功，返回带水印文件}
      400: {description: 水印尚未生成}
      404: {description: 申请或数据文件不存在}
    """
    @jwt_required()
    def post(self):
        data = request.get_json()
        app_id = data.get('application_id')
        algorithm = data.get('algorithm', 'lsb')

        item = Application.query.get(app_id)
        if not item:
            return {'status': False, 'msg': '申请不存在'}, 404

        if not item.qrcode:
            return {'status': False, 'msg': '水印尚未生成'}, 400

        try:
            data_type = (item.data_type or 'vector').lower()

            if data_type == 'raster':
                return self._embed_raster(item, algorithm=algorithm)
            else:
                return self._embed_vector(item)

        except Exception as e:
            logging.error(str(e))
            return {'status': False, 'msg': '操作失败，请稍后重试'}, 500

    def _embed_vector(self, item):
        shp_record = Shp.query.get(item.data_id)
        if not shp_record or not shp_record.shp_file_path:
            return {'status': False, 'msg': f'未找到编号为 {item.data_id} 的矢量数据文件'}, 404

        shp_file = shp_record.shp_file_path
        if not os.path.exists(shp_file):
            candidate = os.path.join(current_app.root_path, shp_file.lstrip('/\\'))
            if os.path.exists(candidate):
                shp_file = candidate
            else:
                return {'status': False, 'msg': '数据文件在服务器上丢失'}, 404

        temp_qr_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp', f'qr_{item.id}.png')
        os.makedirs(os.path.dirname(temp_qr_path), exist_ok=True)
        with open(temp_qr_path, "wb") as fh:
            fh.write(base64.b64decode(item.qrcode))

        try:
            embed_result = vector_embed(shp_file, temp_qr_path)
            zip_path = embed_result['zip_path']
            vr = embed_result['vr']
        finally:
            if os.path.exists(temp_qr_path):
                try:
                    os.remove(temp_qr_path)
                except OSError:
                    pass

        item.watermark_embedded = True
        item.watermark_path = zip_path
        item.vr_data = json.dumps(vr)
        db.session.commit()

        cap = embed_result.get('capacity_report', {})
        log_action(
            item.applicant_user_number, item.applicant_name,
            '矢量水印嵌入', '成功',
            f"app_id={item.id} data_id={item.data_id} vertices={cap.get('total_vertices', 'N/A')} utilization={cap.get('utilization_percent', 'N/A')}%"
        )

        return send_file(zip_path, as_attachment=True, download_name=os.path.basename(zip_path))

    def _embed_raster(self, item, algorithm='lsb'):
        raster_record = RasterData.query.get(item.data_id)
        if not raster_record or not raster_record.raster_file_path:
            return {'status': False, 'msg': f'未找到编号为 {item.data_id} 的栅格数据文件'}, 404

        host_path = raster_record.raster_file_path
        if not os.path.exists(host_path):
            candidate = os.path.join(current_app.root_path, host_path.lstrip('/\\'))
            if os.path.exists(candidate):
                host_path = candidate
            else:
                return {'status': False, 'msg': '数据文件在服务器上丢失'}, 404

        qr_img = Image.open(io.BytesIO(base64.b64decode(item.qrcode))).convert('L')
        out_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'crmark', f'app_{item.id}')
        os.makedirs(out_dir, exist_ok=True)

        if algorithm == 'dwt':
            result = embed_dwt(
                host_path=host_path,
                watermark_img=qr_img,
                output_dir=out_dir,
                prefix=f'app_{item.id}'
            )
        elif algorithm == 'histogram':
            result = embed_histogram(
                host_path=host_path,
                watermark_img=qr_img,
                output_dir=out_dir,
                prefix=f'app_{item.id}'
            )
        else:
            result = embed_reversible(
                host_path=host_path,
                watermark_img=qr_img,
                output_dir=out_dir,
                prefix=f'app_{item.id}'
            )

        # Compute PSNR between original and stego
        psnr_value = None
        try:
            original_img = Image.open(host_path).convert('RGB')
            stego_img = Image.open(result['stego_path']).convert('RGB')
            psnr_value = compute_psnr(original_img, stego_img)
        except Exception as e:
            logging.warning('PSNR computation failed: %s', e)

        item.watermark_embedded = True
        item.watermark_path = result['stego_path']
        item.watermark_path_meta = result.get('wm_meta_path', '')
        item.watermark_path_map = result.get('wm_map_path', '')
        db.session.commit()

        psnr_str = f" psnr={psnr_value:.2f}dB" if psnr_value else ""
        log_action(
            item.applicant_user_number, item.applicant_name,
            '栅格水印嵌入', '成功',
            f"app_id={item.id} data_id={item.data_id} bit_count={result.get('bit_count', 'N/A')} changed={result.get('changed_count', 'N/A')}{psnr_str}"
        )

        return send_file(result['stego_path'], as_attachment=True,
                         download_name=os.path.basename(result['stego_path']))

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

        item = Application.query.get(app_id)
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
            _safe_extract_zip(zip_ref, extract_dir)

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
        qr_text = _decode_qr_from_image(watermark_img_path)
        verify_ok = qr_text is not None
        parsed = _parse_qr_text(qr_text) if qr_text else {}

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
                        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'reason': item.reason,
                        '_qr_raw': qr_text
                    },
                    'parsed': parsed
                }
            }
        }, 200

class UploadOriginalWatermarkResource(Resource):
    """Upload original watermark image for a specific application."""
    @jwt_required()
    def post(self):
        if 'file' not in request.files:
            return {'status': False, 'msg': '没有上传文件'}, 400
        file = request.files['file']
        if file.filename == '':
            return {'status': False, 'msg': '没有选择文件'}, 400
        app_id = request.form.get('application_id')
        if not app_id:
            return {'status': False, 'msg': '缺少申请编号'}, 400

        item = Application.query.get(app_id)
        if not item:
            return {'status': False, 'msg': '申请不存在'}, 404

        try:
            filename = secure_filename(file.filename)
            save_dir = os.path.join(current_app.config['WATERMARK_FOLDER'], 'original')
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, f'app_{item.id}_{filename}')
            file.save(save_path)

            item.watermark_path_map = save_path
            db.session.commit()

            identity = get_jwt_identity() or {}
            log_action(
                identity.get('number', 'unknown'), identity.get('username', 'unknown'),
                '上传原始水印', '成功', f"app_id={item.id}"
            )
            return {'status': True, 'msg': '原始水印上传成功', 'path': save_path}, 200
        except Exception as e:
            logging.error(str(e))
            return {'status': False, 'msg': '上传失败'}, 500


class UploadExtractedWatermarkResource(Resource):
    """Upload extracted watermark image and compute NC against original."""
    @jwt_required()
    def post(self):
        if 'file' not in request.files:
            return {'status': False, 'msg': '没有上传文件'}, 400
        file = request.files['file']
        if file.filename == '':
            return {'status': False, 'msg': '没有选择文件'}, 400
        app_id = request.form.get('application_id')
        if not app_id:
            return {'status': False, 'msg': '缺少申请编号'}, 400

        item = Application.query.get(app_id)
        if not item:
            return {'status': False, 'msg': '申请不存在'}, 404

        try:
            filename = secure_filename(file.filename)
            save_dir = os.path.join(current_app.config['EXTRACTED_FOLDER'], 'uploaded')
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, f'app_{item.id}_{filename}')
            file.save(save_path)

            # Compute NC if original watermark exists
            nc_value = None
            if item.qrcode:
                try:
                    original_img = Image.open(io.BytesIO(base64.b64decode(item.qrcode))).convert('L')
                    extracted_img = Image.open(save_path).convert('L').resize(original_img.size)
                    orig_bits = (np.array(original_img) > 127).astype(int).flatten()
                    extr_bits = (np.array(extracted_img) > 127).astype(int).flatten()
                    nc_value = compute_nc(orig_bits, extr_bits)

                    # Persist verification
                    verification = WatermarkVerification(
                        nc_value=round(nc_value, 6),
                        original_hash=hashlib.sha256(item.qrcode.encode()).hexdigest(),
                        extracted_hash=hashlib.sha256(base64.b64encode(open(save_path, 'rb').read()).decode().encode()).hexdigest(),
                        verified_by=get_jwt_identity().get('number', 'unknown') if isinstance(get_jwt_identity(), dict) else 'unknown',
                        verified_at=datetime.utcnow(),
                        ip_address=request.remote_addr
                    )
                    db.session.add(verification)
                    db.session.commit()
                except Exception as e:
                    logging.warning('NC computation failed: %s', e)

            identity = get_jwt_identity() or {}
            log_action(
                identity.get('number', 'unknown') if isinstance(identity, dict) else 'unknown',
                identity.get('username', 'unknown') if isinstance(identity, dict) else 'unknown',
                '上传提取水印', '成功', f"app_id={item.id} nc={nc_value}"
            )

            result = {'status': True, 'msg': '提取水印上传成功', 'path': save_path}
            if nc_value is not None:
                result['nc_value'] = round(nc_value, 6)
            return result, 200
        except Exception as e:
            logging.error(str(e))
            return {'status': False, 'msg': '上传失败'}, 500


class UploadOriAndExtWatermarkResource(Resource):
    """
    上传原始水印与提取水印进行比对
    ---
    tags: [Watermark]
    security: [Bearer: []]
    consumes: [multipart/form-data]
    parameters:
      - in: formData
        name: originalFile
        type: file
        required: true
        description: 原始水印图片
      - in: formData
        name: extractedFile
        type: file
        required: true
        description: 提取的水印图片
    responses:
      200: {description: 比对完成，返回NC值}
      400: {description: 缺少文件}
    """
    @jwt_required()
    def post(self):
        original_file = request.files.get('originalFile')
        extracted_file = request.files.get('extractedFile')
        if not original_file or not extracted_file:
            return {'status': False, 'msg': '缺少文件'}, 400
        try:
            ori_img = Image.open(original_file.stream).convert('L')
            ext_img = Image.open(extracted_file.stream).convert('L').resize(ori_img.size)
            ori_arr = (np.array(ori_img) > 127).astype(np.uint8)
            ext_arr = (np.array(ext_img) > 127).astype(np.uint8)
            nc_value = float((ori_arr == ext_arr).sum() / ori_arr.size)

            original_file.stream.seek(0)
            extracted_file.stream.seek(0)
            ori_b64 = base64.b64encode(original_file.read()).decode('utf-8')
            ext_b64 = base64.b64encode(extracted_file.read()).decode('utf-8')

            identity = get_jwt_identity() or {}

            # Persist verification result for forensic traceability
            verification = WatermarkVerification(
                nc_value=round(nc_value, 6),
                original_hash=hashlib.sha256(ori_b64.encode()).hexdigest(),
                extracted_hash=hashlib.sha256(ext_b64.encode()).hexdigest(),
                verified_by=identity.get('number', 'unknown'),
                verified_at=datetime.utcnow(),
                ip_address=request.remote_addr
            )
            db.session.add(verification)
            db.session.commit()

            log_action(
                identity.get('number', 'unknown'),
                identity.get('username', 'unknown'),
                '水印比对', '成功',
                f"nc_value={round(nc_value, 6)}"
            )

            return {
                'status': True,
                'nc_value': round(nc_value, 6),
                'original_watermark': ori_b64,
                'extracted_watermark': ext_b64
            }, 200
        except Exception as e:
            logging.error(str(e))
            return {'status': False, 'msg': '操作失败，请稍后重试'}, 500


class GetOriginalWatermarkResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        app_id = data.get('number')
        item = Application.query.get(app_id)
        if not item or not item.qrcode:
            return {'status': False, 'msg': '未找到对应水印'}, 404
        return {'status': True, 'original_watermark': item.qrcode}, 200


class WatermarkVerificationRecordsResource(Resource):
    """List watermark verification records with pagination."""
    @jwt_required()
    def get(self):
        page = request.args.get('page', 1, type=int)
        page_size = min(request.args.get('pageSize', 20, type=int), 100)

        pagination = WatermarkVerification.query.order_by(
            WatermarkVerification.verified_at.desc()
        ).paginate(page=page, per_page=page_size, error_out=False)

        records = []
        for r in pagination.items:
            records.append({
                'id': r.id,
                'nc_value': r.nc_value,
                'original_hash': r.original_hash,
                'extracted_hash': r.extracted_hash,
                'verified_by': r.verified_by,
                'verified_at': r.verified_at.isoformat() if r.verified_at else None,
                'ip_address': r.ip_address
            })

        return {
            'status': True,
            'data': records,
            'pages': {
                'total': pagination.total,
                'page': page,
                'page_size': page_size
            }
        }, 200


class WatermarkPreviewResource(Resource):
    """Preview watermark capacity and expected distortion without embedding."""
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        app_id = data.get('application_id')
        if not app_id:
            return {'status': False, 'msg': '缺少申请编号'}, 400

        item = Application.query.get(app_id)
        if not item:
            return {'status': False, 'msg': '申请不存在'}, 404

        data_type = (item.data_type or 'vector').lower()

        try:
            if data_type == 'raster':
                return self._preview_raster(item, data)
            else:
                return self._preview_vector(item, data)
        except Exception as e:
            logging.error(str(e))
            return {'status': False, 'msg': '预览失败'}, 500

    def _preview_vector(self, item, data):
        from algorithm.get_coor import get_coor_nested
        from algorithm.quality_metrics import capacity_report
        import geopandas as gpd

        shp_record = Shp.query.get(item.data_id)
        if not shp_record or not shp_record.shp_file_path:
            return {'status': False, 'msg': '未找到矢量数据'}, 404

        shp_file = shp_record.shp_file_path
        if not os.path.exists(shp_file):
            candidate = os.path.join(current_app.root_path, shp_file.lstrip('/\\'))
            if os.path.exists(candidate):
                shp_file = candidate
            else:
                return {'status': False, 'msg': '数据文件丢失'}, 404

        n = data.get('n', 4)
        side_length = data.get('side_length', 45)

        shpfile = gpd.read_file(shp_file)
        coor_nested, feature_type = get_coor_nested(shpfile)

        # Count total vertices
        total_vertices = 0
        for i in range(coor_nested.shape[1]):
            arr = coor_nested[:, i][0]
            if isinstance(arr, np.ndarray):
                if arr.ndim == 1:
                    total_vertices += arr.size
                else:
                    total_vertices += sum(a.size for a in arr)
            else:
                total_vertices += 1

        # Calculate watermark bit count
        n_bits_needed = side_length ** 2 - 192  # minus detection patterns
        cap = capacity_report(total_vertices, n_bits_needed, n)

        return {
            'status': True,
            'data_type': 'vector',
            'preview': {
                'total_vertices': total_vertices,
                'watermark_bits': n_bits_needed,
                'capacity': cap,
                'params': {'n': n, 'side_length': side_length},
                'estimated_utilization': cap['utilization_percent']
            }
        }, 200

    def _preview_raster(self, item, data):
        from algorithm.quality_metrics import capacity_report

        raster_record = RasterData.query.get(item.data_id)
        if not raster_record or not raster_record.raster_file_path:
            return {'status': False, 'msg': '未找到栅格数据'}, 404

        host_path = raster_record.raster_file_path
        if not os.path.exists(host_path):
            candidate = os.path.join(current_app.root_path, host_path.lstrip('/\\'))
            if os.path.exists(candidate):
                host_path = candidate
            else:
                return {'status': False, 'msg': '数据文件丢失'}, 404

        host_img = Image.open(host_path)
        w, h = host_img.size
        total_pixels = w * h

        min_wm = data.get('min_wm_size', 64)
        max_wm = data.get('max_wm_size', 512)
        wm_w = max(min_wm, min(max_wm, w))
        wm_h = max(min_wm, min(max_wm, h))
        bit_count = wm_w * wm_h

        cap = capacity_report(total_pixels, bit_count, n=1)

        return {
            'status': True,
            'data_type': 'raster',
            'preview': {
                'host_size': {'width': w, 'height': h},
                'total_pixels': total_pixels,
                'watermark_size': {'width': wm_w, 'height': wm_h},
                'watermark_bits': bit_count,
                'capacity': cap,
                'estimated_utilization': cap['utilization_percent']
            }
        }, 200


class BatchGenerateWatermarkResource(Resource):
    """
    批量生成水印二维码
    ---
    tags: [Watermark]
    security: [Bearer: []]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [application_ids]
          properties:
            application_ids:
              type: array
              items: {type: integer}
              description: 申请编号列表
            purpose: {type: string, description: 用途}
            usage_scope: {type: string, description: 使用范围}
            security_level: {type: string, description: 安全级别}
            custom_tag: {type: string, description: 自定义标签}
            reason: {type: string, description: 原因}
    responses:
      200: {description: 批量水印生成完成}
      400: {description: 参数错误}
    """
    @admin_required
    def post(self):
        data = request.get_json() or {}
        app_ids = data.get('application_ids')

        if not app_ids or not isinstance(app_ids, list):
            return {'status': False, 'msg': '缺少 application_ids 列表'}, 400

        results = []
        success_count = 0
        fail_count = 0

        for app_id in app_ids:
            try:
                item = Application.query.get(app_id)
                if not item:
                    results.append({'id': app_id, 'success': False, 'error': '申请不存在'})
                    fail_count += 1
                    continue

                # Build QR content with signature
                qr_content, signature = _build_qr_text(item, data)

                # Auto-detect QR version based on content length
                qr_version = _get_qr_version(len(qr_content))

                # Generate QR code
                qr = qrcode.QRCode(
                    version=qr_version,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=10,
                    border=4,
                )
                qr.add_data(qr_content)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")

                # Convert to base64
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()

                # Save all metadata to database
                item.qrcode = img_str
                item.watermark_generated = True
                item.qr_version = qr_version
                item.qr_signature = signature
                item.generation_timestamp = datetime.utcnow()

                # Save optional fields
                for field in ['purpose', 'usage_scope', 'security_level', 'custom_tag']:
                    if data.get(field):
                        setattr(item, field, str(data.get(field)).strip())

                if data.get('reason'):
                    item.reason = str(data.get('reason')).strip()

                db.session.commit()

                log_action(
                    item.applicant_user_number, item.applicant_name,
                    '批量水印生成', '成功',
                    f"app_id={item.id} data_alias={item.data_alias} qr_version={qr_version}"
                )
                record_watermark(data_type=item.data_type or 'vector')

                results.append({'id': app_id, 'success': True, 'qr_version': qr_version})
                success_count += 1

            except Exception as e:
                logging.error(f"Batch generate watermark failed for app_id={app_id}: {e}")
                db.session.rollback()
                results.append({'id': app_id, 'success': False, 'error': str(e)})
                fail_count += 1

        return {
            'status': True,
            'results': results,
            'summary': {
                'total': len(app_ids),
                'success': success_count,
                'failed': fail_count
            }
        }, 200


class BatchEmbedWatermarkResource(Resource):
    """
    批量嵌入水印到数据文件
    ---
    tags: [Watermark]
    security: [Bearer: []]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [application_ids]
          properties:
            application_ids:
              type: array
              items: {type: integer}
              description: 申请编号列表
    responses:
      200: {description: 批量水印嵌入完成}
      400: {description: 参数错误}
    """
    @admin_required
    def post(self):
        data = request.get_json() or {}
        app_ids = data.get('application_ids')

        if not app_ids or not isinstance(app_ids, list):
            return {'status': False, 'msg': '缺少 application_ids 列表'}, 400

        results = []
        success_count = 0
        fail_count = 0

        for app_id in app_ids:
            try:
                item = Application.query.get(app_id)
                if not item:
                    results.append({'id': app_id, 'success': False, 'error': '申请不存在'})
                    fail_count += 1
                    continue

                if not item.qrcode:
                    results.append({'id': app_id, 'success': False, 'error': '水印尚未生成'})
                    fail_count += 1
                    continue

                data_type = (item.data_type or 'vector').lower()

                if data_type == 'raster':
                    self._embed_raster(item)
                else:
                    self._embed_vector(item)

                results.append({'id': app_id, 'success': True, 'data_type': data_type})
                success_count += 1

            except Exception as e:
                logging.error(f"Batch embed watermark failed for app_id={app_id}: {e}")
                db.session.rollback()
                results.append({'id': app_id, 'success': False, 'error': str(e)})
                fail_count += 1

        return {
            'status': True,
            'results': results,
            'summary': {
                'total': len(app_ids),
                'success': success_count,
                'failed': fail_count
            }
        }, 200

    def _embed_vector(self, item):
        shp_record = Shp.query.get(item.data_id)
        if not shp_record or not shp_record.shp_file_path:
            raise ValueError(f'未找到编号为 {item.data_id} 的矢量数据文件')

        shp_file = shp_record.shp_file_path
        if not os.path.exists(shp_file):
            candidate = os.path.join(current_app.root_path, shp_file.lstrip('/\\'))
            if os.path.exists(candidate):
                shp_file = candidate
            else:
                raise ValueError('数据文件在服务器上丢失')

        temp_qr_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp', f'qr_{item.id}.png')
        os.makedirs(os.path.dirname(temp_qr_path), exist_ok=True)
        with open(temp_qr_path, "wb") as fh:
            fh.write(base64.b64decode(item.qrcode))

        try:
            embed_result = vector_embed(shp_file, temp_qr_path)
            zip_path = embed_result['zip_path']
            vr = embed_result['vr']
        finally:
            if os.path.exists(temp_qr_path):
                try:
                    os.remove(temp_qr_path)
                except OSError:
                    pass

        item.watermark_embedded = True
        item.watermark_path = zip_path
        item.vr_data = json.dumps(vr)
        db.session.commit()

        cap = embed_result.get('capacity_report', {})
        log_action(
            item.applicant_user_number, item.applicant_name,
            '批量矢量水印嵌入', '成功',
            f"app_id={item.id} data_id={item.data_id} vertices={cap.get('total_vertices', 'N/A')} utilization={cap.get('utilization_percent', 'N/A')}%"
        )

    def _embed_raster(self, item):
        raster_record = RasterData.query.get(item.data_id)
        if not raster_record or not raster_record.raster_file_path:
            raise ValueError(f'未找到编号为 {item.data_id} 的栅格数据文件')

        host_path = raster_record.raster_file_path
        if not os.path.exists(host_path):
            candidate = os.path.join(current_app.root_path, host_path.lstrip('/\\'))
            if os.path.exists(candidate):
                host_path = candidate
            else:
                raise ValueError('数据文件在服务器上丢失')

        qr_img = Image.open(io.BytesIO(base64.b64decode(item.qrcode))).convert('L')
        out_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'crmark', f'app_{item.id}')
        os.makedirs(out_dir, exist_ok=True)
        result = embed_reversible(
            host_path=host_path,
            watermark_img=qr_img,
            output_dir=out_dir,
            prefix=f'app_{item.id}'
        )

        # Compute PSNR between original and stego
        psnr_value = None
        try:
            original_img = Image.open(host_path).convert('RGB')
            stego_img = Image.open(result['stego_path']).convert('RGB')
            psnr_value = compute_psnr(original_img, stego_img)
        except Exception as e:
            logging.warning('PSNR computation failed: %s', e)

        item.watermark_embedded = True
        item.watermark_path = result['stego_path']
        item.watermark_path_meta = result.get('wm_meta_path', '')
        item.watermark_path_map = result.get('wm_map_path', '')
        db.session.commit()

        psnr_str = f" psnr={psnr_value:.2f}dB" if psnr_value else ""
        log_action(
            item.applicant_user_number, item.applicant_name,
            '批量栅格水印嵌入', '成功',
            f"app_id={item.id} data_id={item.data_id} bit_count={result.get('bit_count', 'N/A')} changed={result.get('changed_count', 'N/A')}{psnr_str}"
        )

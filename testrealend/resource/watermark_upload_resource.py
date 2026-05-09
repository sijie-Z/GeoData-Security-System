from flask import request, current_app
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from model.Application import Application
from extension.extension import db
from datetime import datetime, timezone
import os
import base64
import hashlib
import io
import json
import numpy as np
import logging
from PIL import Image
from model.Shp_Data import Shp
from model.Raster_Data import RasterData
from model.watermark_verification import WatermarkVerification
from werkzeug.utils import secure_filename
from utils.log_helper import log_action
from utils.required import admin_required
from resource.watermark_utils import (
    safe_extract_zip, QR_SECRET_KEY, decode_qr_from_image,
    parse_qr_text, build_qr_text, get_qr_version
)
from algorithm.embed import embed as vector_embed
from algorithm.raster_reversible_watermark import embed_reversible
from algorithm.quality_metrics import compute_nc, compute_psnr
from utils.metrics import record_watermark


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

        item = db.session.get(Application, app_id)
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

        item = db.session.get(Application, app_id)
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
                        verified_at=datetime.now(timezone.utc),
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
                verified_at=datetime.now(timezone.utc),
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
        item = db.session.get(Application, app_id)
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

        item = db.session.get(Application, app_id)
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

        shp_record = db.session.get(Shp, item.data_id)
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

        raster_record = db.session.get(RasterData, item.data_id)
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
                item = db.session.get(Application, app_id)
                if not item:
                    results.append({'id': app_id, 'success': False, 'error': '申请不存在'})
                    fail_count += 1
                    continue

                # Build QR content with signature
                qr_content, signature = build_qr_text(item, data)

                # Auto-detect QR version based on content length
                qr_version = get_qr_version(len(qr_content))

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
                item.generation_timestamp = datetime.now(timezone.utc)

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
                item = db.session.get(Application, app_id)
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
        shp_record = db.session.get(Shp, item.data_id)
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
        raster_record = db.session.get(RasterData, item.data_id)
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


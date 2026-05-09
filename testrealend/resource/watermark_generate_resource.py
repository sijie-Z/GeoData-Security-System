from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required
from model.Application import Application
from extension.extension import db
from datetime import datetime, timezone
import base64
import qrcode
import io
from utils.log_helper import log_action
from resource.watermark_utils import (
    build_qr_text, get_qr_version
)
from utils.metrics import record_watermark


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

        item = db.session.get(Application, app_id)
        if not item:
            return {'status': False, 'msg': '申请不存在'}, 404

        try:
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


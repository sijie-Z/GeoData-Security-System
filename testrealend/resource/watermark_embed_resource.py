from flask import request, current_app, send_file
from flask_restful import Resource
from flask_jwt_extended import jwt_required
from model.Application import Application
from extension.extension import db
import os
import base64
import io
import json
import logging
from PIL import Image
from model.Shp_Data import Shp
from model.Raster_Data import RasterData
from utils.log_helper import log_action
from algorithm.embed import embed as vector_embed
from algorithm.raster_reversible_watermark import embed_reversible
from algorithm.raster_dwt_watermark import embed_dwt
from algorithm.raster_histogram_watermark import embed_histogram
from algorithm.quality_metrics import compute_psnr


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

        item = db.session.get(Application, app_id)
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
        shp_record = db.session.get(Shp, item.data_id)
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
        raster_record = db.session.get(RasterData, item.data_id)
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


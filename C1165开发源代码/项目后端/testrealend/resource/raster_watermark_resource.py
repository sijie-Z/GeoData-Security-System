from flask import request, send_file, jsonify
from flask_restful import Resource, reqparse
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import os
import base64
import traceback
from server.raster_watermark_server import RasterWatermarkServer
from flask import current_app


class RasterEmbedResource(Resource):
    """
    处理栅格水印嵌入请求的资源。
    """
    def post(self):
        try:
            data = request.get_json()
            application_id = data.get('application_id')

            if not application_id:
                return jsonify({'msg': '未传输application_id'}), 400

            result = RasterWatermarkServer.embed_watermark(application_id)
            
            if result.get("success"):
                return send_file(result["stego_path"], as_attachment=True, download_name=result["filename"])
            else:
                return jsonify({'msg': result.get("message", "水印嵌入失败")}), 500
        except Exception as e:
            traceback.print_exc()
            return jsonify({'msg': f"服务器内部错误: {str(e)}"}), 500


class RasterExtractResource(Resource):
    """
    处理栅格水印提取请求的资源。
    """
    def post(self):
        temp_path = None
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('application_id', type=int, required=True, location='form')
            parser.add_argument('file', type=FileStorage, location='files', required=True)
            args = parser.parse_args()
            
            uploaded_file = args['file']
            app_id = args['application_id']
            
            if not uploaded_file.filename:
                return jsonify({'msg': '上传文件为空'}), 400

            temp_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            filename = secure_filename(uploaded_file.filename)
            temp_path = os.path.join(temp_dir, filename)
            uploaded_file.save(temp_path)
            
            result = RasterWatermarkServer.extract_watermark(temp_path, app_id)

            if result.get("success"):
                encoded_string = base64.b64encode(result["extracted_binary"]).decode('utf-8')
                return jsonify({
                    "status": True,
                    "msg": "水印提取成功",
                    "data": {"watermark_base64": encoded_string}
                }), 200
            else:
                return jsonify({'msg': result.get("message", "水印提取失败")}), 500
        except Exception as e:
            traceback.print_exc()
            return jsonify({'msg': f"服务器内部错误: {str(e)}"}), 500
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError as e:
                    print(f"Error deleting temp file {temp_path}: {e}")

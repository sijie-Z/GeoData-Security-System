import os
import zipfile
from flask import request, current_app, jsonify
from flask_restful import Resource
from werkzeug.utils import secure_filename
import logging
import traceback
import base64

# 修复：使用正确的算法模块路径
from algorithm.extract import extract
from model.Embed_File_Record import EmbedFileRecord

def _safe_extract(zip_file, dest_dir):
    """安全解压，防止Zip Slip攻击"""
    for member in zip_file.namelist():
        # 计算目标路径，确保在目标目录内
        target_path = os.path.realpath(os.path.join(dest_dir, member))
        if not target_path.startswith(os.path.realpath(dest_dir)):
            raise ValueError(f"非法文件路径: {member}")
    # 所有路径安全后执行解压
    zip_file.extractall(dest_dir)

class UploadFile(Resource):
    def post(self):
        try:
            # 1. 获取数据编号
            data_number = request.form.get('dataNumber')
            logging.info(f"Received data number: {data_number}")

            if not data_number:
                logging.error("Data number not provided in the request.")
                return {"error": "数据编号未提供"}, 400

            # 2. 从数据库中查询记录
            record = EmbedFileRecord.query.filter_by(data_id=data_number).first()

            # 3. 关键修复：检查记录是否存在
            if not record:
                logging.error(f"No record found for data_id: {data_number}")
                return {"error": f"未找到数据编号 {data_number} 对应的记录，请检查编号是否正确。"}, 404

            # 4. 获取 vr 属性
            vr = record.vr
            logging.info(f"Found vr value: {vr}")

            # 5. 验证文件部分
            if 'file' not in request.files:
                logging.error("No file part in the request.")
                return {"error": "请求中未包含文件部分"}, 400

            file = request.files['file']

            if file.filename == '':
                logging.error("No file selected for upload.")
                return {"error": "未选择要上传的文件"}, 400

            if not (file and file.filename.endswith('.zip')):
                logging.error("Uploaded file is not a ZIP file.")
                return {"error": "上传的文件必须是ZIP格式"}, 400

            # 6. 处理文件
            # 使用 with 语句来管理 ZIP 文件的上下文
            with zipfile.ZipFile(file) as zip_file:
                # 检查 ZIP 文件中包含的 .shp 文件
                shp_files = [f for f in zip_file.namelist() if f.endswith('.shp')]

                if len(shp_files) != 1:
                    logging.error("ZIP file must contain exactly one .shp file.")
                    return {"error": "ZIP文件必须包含且仅包含一个.shp文件"}, 400

                # 验证通过，保存文件
                filename = secure_filename(file.filename)
                save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(save_path)
                logging.info(f'文件已保存到: {save_path}')

                # 解压后的目录路径
                extract_dir_name = os.path.splitext(filename)[0]
                extract_dir = os.path.join(os.path.dirname(save_path), extract_dir_name)

                os.makedirs(extract_dir, exist_ok=True)
                _safe_extract(zip_file, extract_dir)
                logging.info(f'文件已解压到: {extract_dir}')

            # 7. 调用提取算法
            output_shapefile_path, output_watermark_path = extract(extract_dir, vr)
            logging.info(f"Watermark extracted to: {output_watermark_path}")

            # 8. 将水印文件转换为Base64编码
            if not os.path.exists(output_watermark_path):
                logging.error(f"Extracted watermark file not found at: {output_watermark_path}")
                return {"error": "提取水印失败，文件不存在。"}, 500

            with open(output_watermark_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

            # 9. 返回Base64编码的水印图片
            return jsonify({
                "message": f"文件 {filename} 上传并成功解压。",
                "extract_dir": extract_dir,
                "watermark_base64": encoded_string
            })

        except Exception as e:
            # 捕获所有其他潜在错误
            traceback.print_exc()
            logging.error(f"An unexpected error occurred: {str(e)}")
            return {"error": "操作失败，请稍后重试"}, 500
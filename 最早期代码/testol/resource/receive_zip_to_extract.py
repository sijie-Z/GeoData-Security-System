import zipfile
from model.Embed_File_Record import EmbedFileRecord
from algorithm.extract import extract
import base64
import os
import logging
from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename
from flask_restful import Resource
from algorithm.NC import NC, image_to_array
from model.Application import Application
from flask.globals import g


class UploadFile(Resource):
    def post(self):

        # 获取数据编号，以便查询vr值
        data_number = request.form.get('dataNumber')
        print(data_number)

        # 获取记录中
        query = EmbedFileRecord.query.filter_by(data_id=data_number)
        record = query.first()

        if not data_number:
            logging.error("Data number not provided in the request.")
            return {"message": "数据编号未提供"}, 400

        if 'file' not in request.files:
            logging.error("No file part in the request.")
            return {"error": "请求中未包含文件部分"}, 400

        file = request.files['file']

        if file.filename == '':
            logging.error("No file selected for upload.")
            return {"error": "未选择要上传的文件"}, 400

        # 验证文件是否是 zip 文件
        if not (file and file.filename.endswith('.zip')):
            logging.error("Uploaded file is not a ZIP file.")
            return {"error": "上传的文件必须是ZIP格式"}, 400

        try:
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

                # 解压后的目录路径，使用文件名去掉 .zip 后缀
                extract_dir_name = os.path.splitext(filename)[0]
                extract_dir = os.path.join(os.path.dirname(save_path), extract_dir_name)

                # 创建解压目录（如果不存在的话）
                os.makedirs(extract_dir, exist_ok=True)

                # 解压 ZIP 文件中的所有文件
                zip_file.extractall(extract_dir)
                logging.info(f'文件已解压到: {extract_dir}')

            # 获取提取到的水印路径output_watermark_path， 需要传入对应的zip文件目录   以及嵌入记录中对应数据编号所对应的vr值
            output_shapefile_path, output_watermark_path = extract(extract_dir, record.vr)
            print(output_watermark_path)

            # 设置全局变量
            g.output_watermark_path = output_watermark_path

            # 将水印文件转换为Base64编码
            with open(output_watermark_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

            # 返回Base64编码的水印图片
            return jsonify({
                "message": f"文件 {filename} 上传并成功解压。",
                "extract_dir": extract_dir,
                "watermark_base64": encoded_string  # 返回Base64编码的字符串
            })

        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            return {"error": str(e)}, 500


class GetOriginalWatermark(Resource):
    def post(self):
        number = request.json.get('number')
        print(number)

        if not number:
            return jsonify({
                'status': False,
                'message': '数据编号未提供'
            })

        get_original_watermark = Application.query.filter_by(id=number).first()

        if not get_original_watermark:
            return jsonify({
                'status': False,
                'message': '未找到对应的申请记录'
            })

        record = get_original_watermark.QRcode

        record_base64 = base64.b64encode(record).decode('utf-8')

        return jsonify({
            'status': True,
            'original_watermark': record_base64
        })


class UploadWatermarks(Resource):
    def post(self):
        # 检查是否有上传文件
        if 'originalFile' not in request.files or 'extractedFile' not in request.files:
            return jsonify({
                'status': False,
                'msg': '请同时上传原始水印文件和提取出的水印文件'
            })

        # 获取原始水印文件
        original_file = request.files['originalFile']
        if original_file.filename == '':
            return jsonify({
                'status': False,
                'msg': '原始水印文件未选择'
            })

        # 获取提取出的水印文件
        extracted_file = request.files['extractedFile']
        if extracted_file.filename == '':
            return jsonify({
                'status': False,
                'msg': '提取出的水印文件未选择'
            })

        # 保存原始水印文件
        original_filename = secure_filename(original_file.filename)
        original_upload_dir = os.path.join(os.getcwd(), 'compare/uploads/original_watermark')
        if not os.path.exists(original_upload_dir):
            os.makedirs(original_upload_dir)
        original_file_path = os.path.join(original_upload_dir, original_filename)
        original_file.save(original_file_path)

        # 保存提取出的水印文件
        extracted_filename = secure_filename(extracted_file.filename)
        extracted_upload_dir = os.path.join(os.getcwd(), 'compare/uploads/extracted_watermark')
        if not os.path.exists(extracted_upload_dir):
            os.makedirs(extracted_upload_dir)
        extracted_file_path = os.path.join(extracted_upload_dir, extracted_filename)
        extracted_file.save(extracted_file_path)

        # print(original_file_path)
        # print(extracted_file_path)

        # # 获取nc值
        #
        # nc_value = NC(original_file_path, extracted_file_path)

        # 先加载图像文件为数组
        original_watermark_array = image_to_array(original_file_path)
        extracted_watermark_array = image_to_array(extracted_file_path)

        # 然后传递数组给NC函数
        nc_value = NC(original_watermark_array, extracted_watermark_array)

        if nc_value:
            return jsonify({
                'status': True,
                'msg': '文件成功上传',
                'original_watermark': original_file_path,
                'extracted_watermark': extracted_file_path,
                'nc_value': nc_value
            })

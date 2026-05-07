import os

from flask import request, jsonify, send_file
from flask_restful import Resource
from model.Application import Application
from model.Shp_Data import Shp
from model.Embed_File_Record import EmbedFileRecord
from io import BytesIO
from PIL import Image
import base64
from datetime import datetime
from algorithm.embed import embed
from algorithm.is_multiple import is_multiple
from extension.extension import db

from model.SendFileRecord import SendFileRecord


class GetAppQRcode(Resource):
    def post(self):
        data = request.get_json()

        if 'application_id' not in data or 'data_id' not in data or 'applicant_user_number' not in data:
            return jsonify({'msg': '未传输表单数据'})

        application_id = data.get('application_id')
        data_id = data.get('data_id')
        applicant_user_number = data.get('applicant_user_number')
        embed_person = data.get('embed_person')
        applicant = data.get('applicant')

        application_result = Application.query.filter_by(id=application_id).first()
        shpfile_data = Shp.query.filter_by(id=data_id).first()

        if not application_result or not shpfile_data:
            return jsonify({'msg': '未搜索到数据'})

        shpfile_path = shpfile_data.shp_file_path
        QRcode_binary = application_result.qrcode

        qr_image = Image.open(BytesIO(QRcode_binary))
        watermark_path = 'temp_qrcode.png'
        qr_image.save(watermark_path)

        current_time = datetime.now().strftime('%Y%m%d%H%M%S')
        output_filename = f"{application_id}_{applicant_user_number}_{current_time}.shp"

        is_multiple(shpfile_path)
        zip_file_path, vr = embed(shpfile_path, watermark_path, output_filename)

        if zip_file_path:
            # 使用 os.path.basename() 仅提取文件名
            file_name = os.path.basename(zip_file_path)

            embed_watermark_record = EmbedFileRecord(
                application_id=application_id,
                data_id=data_id,
                embed_person=embed_person,
                applicant=applicant,
                generate_filename=file_name,
                generate_file_path=zip_file_path,
                embed_time=current_time,
                vr=vr

            )
            db.session.add(embed_watermark_record)
            db.session.commit()

            record_send_file = SendFileRecord(
                application_id=application_id,
                data_id=data_id,
                send_person=embed_person,
                applicant=applicant,
                filename=file_name,
                file_path=zip_file_path,
                send_time=current_time,
                vr=vr

            )
            db.session.add(record_send_file)
            db.session.commit()

            return send_file(zip_file_path, as_attachment=True, download_name=file_name)

        else:
            return jsonify({'msg': '水印嵌入失败'})

from flask import Flask, request, jsonify
import qrcode
import io
from extension.extension import db
from model.Application import Application
from flask_restful import Resource


class GenerateQrcodeResource(Resource):
    def post(self):
        try:
            data = request.json
            application_id = data.get('application_id')
            data_id = data.get('data_id')
            data_alias = data.get('data_alias')
            # data_name = data.get('data_name')
            # print(data_name)
            applicant_name = data.get('applicant_name')
            applicant_user_number = data.get('applicant_user_number')
            adm1_name = data.get('adm1_name')
            adm2_name = data.get('adm2_name')
            now = data.get('now')

            if not application_id:
                return jsonify({'status': False, 'msg': '缺少 application_id'})

            # 查找申请记录
            record = Application.query.filter_by(id=application_id).first()
            if not record:
                return jsonify({'status': False, 'msg': '申请记录未找到'})

            # 检查QRcode字段是否为null
            if record.QRcode is not None:
                return jsonify({'status': False, 'msg': 'QR码已存在，不能重复生成'})

            # 生成QR码内容
            qr_content = f"Application ID: {application_id}\nData ID: {data_id}\nData Name: {data_alias}\n" \
                         f"Applicant: {applicant_name} ({applicant_user_number})\n" \
                         f"Admin1: {adm1_name}\nAdmin2: {adm2_name}\nGenerated at: {now}"

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=1,
                border=0,
            )
            qr.add_data(qr_content)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # 将QR码转换为二进制数据
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            qr_code_data = buffered.getvalue()

            # 更新数据库中的QRcode字段
            record.QRcode = qr_code_data
            db.session.commit()

            return jsonify({'status': True, 'msg': 'QR码生成并保存成功'})

        except Exception as e:
            print(f'Error: {e}')
            return jsonify({'status': False, 'msg': '服务器错误'})

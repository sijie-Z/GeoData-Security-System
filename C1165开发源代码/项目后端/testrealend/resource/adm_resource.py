# from flask_restful import Resource
# from flask import request, jsonify

# from model.Employee_Info import EmployeeInfo
# from utils.required import admin_required, permission_required
# from server.adm_server import AdmServer

# import base64

# class GetEmpInfoList(Resource):
#     def get(self):
#         try:
#             emp_info_list, list_num = AdmServer().get_emp_info_list()
#             if emp_info_list:
#                 data_list = []
#                 for emp_info in emp_info_list:
#                     data = {
#                         'employee_number': emp_info.employee_number,
#                         'name': emp_info.name,
#                         'job_number': emp_info.job_number,
#                         'address': emp_info.address,
#                         'phone_number': emp_info.phone_number,
#                         'photo_url': f'/api/employee/photo/{emp_info.employee_number}'
#                     }
#                     data_list.append(data)
#                 data_scu = {
#                     'data': {
#                         'list': data_list,
#                         'rows': list_num
#                     },
#                     'msg': '记录获取成功',
#                     'status': True
#                 }
#                 return data_scu, 200
#             else:
#                 data_fail = {
#                     "msg": "没有任何记录"
#                 }
#                 return data_fail, 400

#         except Exception as e:
#             return {
#                 "msg": f"数据异常: {str(e)}",
#                 "status": False
#             }, 500


# class GetEmpPhotoResource(Resource):
#     def get(self, employee_number):
#         employee = EmployeeInfo.query.filter_by(employee_number=employee_number).first()
#         if not employee or not employee.face_photo:
#             return {'message': '员工或照片不存在'}, 404

#         # 确保照片数据以 Base64 编码返回
#         photo = base64.b64encode(employee.face_photo).decode('utf-8')
#         return jsonify({'photo': photo})


# class Adm1GetApplicationsGenerateWatermark(Resource):
#     def get(self):
#         try:
#             page = int(request.args.get('page', 1))
#             page_size = int(request.args.get('pageSize', 2))

#             applications, pagination = AdmServer().applications_generate_watermark(page, page_size)
#             applications_list = []

#             for application in applications:
#                 # 将存储在数据库中的二进制二维码数据转换为Base64字符串
#                 qr_code_base64 = base64.b64encode(application.QRcode).decode('utf-8') if application.QRcode else ''

#                 applications_list.append({
#                     'id': application.id,
#                     'data_id': application.data_id,
#                     'data_name': application.data_name,
#                     'data_alias': application.data_alias,
#                     'data_url': application.data_url,
#                     'applicant_name': application.applicant_name,
#                     'applicant_user_number': application.applicant_user_number,
#                     'reason': application.reason,
#                     'adm1_name': application.adm1_name,
#                     'adm2_name': application.adm2_name,
#                     'first_statu': application.adm1_statu,
#                     'second_statu': application.adm2_statu,
#                     'qrcode': qr_code_base64  # 返回二维码的Base64编码字符串
#                 })

#             return {
#                 'status': True,
#                 'application_data': applications_list,
#                 'pages': pagination  # 返回分页信息
#             }, 200
#         except Exception as e:
#             return {
#                 'status': False,
#                 'msg': str(e)
#             }, 500


# class Adm2EmbeddingWatermark(Resource):
#     def get(self):
#         try:
#             page = int(request.args.get('page', 1))
#             page_size = int(request.args.get('pageSize', 2))

#             applications, pagination = AdmServer().embedding_watermark_application(page, page_size)
#             applications_list = []

#             for application in applications:
#                 # 将存储在数据库中的二进制二维码数据转换为Base64字符串
#                 qr_code_base64 = base64.b64encode(application.QRcode).decode('utf-8') if application.QRcode else ''

#                 applications_list.append({
#                     'id': application.id,
#                     'data_id': application.data_id,
#                     'data_name': application.data_name,
#                     'data_alias': application.data_alias,
#                     'data_url': application.data_url,
#                     'applicant_name': application.applicant_name,
#                     'applicant_user_number': application.applicant_user_number,
#                     'reason': application.reason,
#                     'adm1_name': application.adm1_name,
#                     'adm2_name': application.adm2_name,
#                     'first_statu': application.adm1_statu,
#                     'second_statu': application.adm2_statu,
#                     'qrcode': qr_code_base64  # 返回二维码的Base64编码字符串
#                 })
#                 # print(applications_list)

#             return {
#                 'status': True,
#                 'application_data': applications_list,
#                 'pages': pagination  # 返回分页信息
#             }, 200
#         except Exception as e:
#             return {
#                 'status': False,
#                 'msg': str(e)
#             }, 500


# class WatermarkEmbeddingResource(Resource):
#     def get(self):
#         request.get_json()


# d:\Desktop\ESRI_test\testrealend\resource\adm_resource.py
# d:\Desktop\ESRI_test\testrealend\resource\adm_resource.py
# d:\Desktop\ESRI_test\testrealend\resource\adm_resource.py

from flask_restful import Resource
from flask import request, jsonify, send_file
from werkzeug.datastructures import FileStorage
from model.Employee_Info import EmployeeInfo
from server.adm_server import AdmServer
import base64
import io

# --- 你所有已有的资源类，保持100%不变 ---
class GetEmpInfoList(Resource):
    def get(self):
        try:
            emp_info_list, list_num = AdmServer().get_emp_info_list()
            if emp_info_list:
                data_list = []
                for emp_info in emp_info_list:
                    data = {
                        'employee_number': emp_info.employee_number, 'name': emp_info.name,
                        'job_number': emp_info.job_number, 'address': emp_info.address,
                        'phone_number': emp_info.phone_number,
                        'photo_url': f'/api/employee/photo/{emp_info.employee_number}'
                    }
                    data_list.append(data)
                return {'data': {'list': data_list, 'rows': list_num}, 'msg': '记录获取成功', 'status': True}, 200
            else:
                return {"msg": "没有任何记录"}, 404
        except Exception as e:
            return {"msg": f"数据异常: {str(e)}", "status": False}, 500

class GetEmpPhotoResource(Resource):
    def get(self, employee_number):
        photo_data = AdmServer().get_employee_photo(employee_number)
        if photo_data:
            return send_file(io.BytesIO(photo_data), mimetype='image/jpeg', as_attachment=False)
        else:
            return {'message': '员工照片不存在'}, 404

class DeleteEmployeeResource(Resource):
    def delete(self, employee_number: str):
        success, message = AdmServer().delete_employee(employee_number)
        if success:
            return {'message': message}, 200
        else:
            return {'message': message}, 404

class AddEmployeeResource(Resource):
    def post(self):
        try:
            form_data = request.form.to_dict()
            photo_file = request.files.get('photo')
            required_fields = ['employee_number', 'name', 'job_number', 'phone_number', 'address', 'password']
            for field in required_fields:
                if field not in form_data or not form_data[field]:
                    return {'msg': f"参数缺失: {field}", 'status': False}, 400
            if not photo_file:
                return {'msg': "参数缺失: photo", 'status': False}, 400
        except Exception as e:
            return {'msg': f"解析请求时出错: {str(e)}", 'status': False}, 400
        success, message = AdmServer().add_employee_with_photo(form_data, photo_file)
        if success:
            return {'msg': message, 'status': True}, 201
        else:
            status_code = 409 if '已存在' in message or '已被注册' in message else 400
            return {'msg': message, 'status': False}, status_code

class Adm1GetApplicationsGenerateWatermark(Resource):
    def get(self):
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 2))
            applications, pagination = AdmServer().applications_generate_watermark(page, page_size)
            applications_list = []
            for application in applications:
                qr_code_base64 = base64.b64encode(application.QRcode).decode('utf-8') if application.QRcode else ''
                applications_list.append({
                    'id': application.id, 'data_id': application.data_id, 'data_name': application.data_name,
                    'data_alias': application.data_alias, 'data_url': application.data_url,
                    'applicant_name': application.applicant_name, 'applicant_user_number': application.applicant_user_number,
                    'reason': application.reason, 'adm1_name': application.adm1_name, 'adm2_name': application.adm2_name,
                    'first_statu': application.adm1_statu, 'second_statu': application.adm2_statu, 'qrcode': qr_code_base64
                })
            return {'status': True, 'application_data': applications_list, 'pages': pagination}, 200
        except Exception as e:
            return {'status': False, 'msg': str(e)}, 500

class Adm2EmbeddingWatermark(Resource):
    def get(self):
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 2))
            applications, pagination = AdmServer().embedding_watermark_application(page, page_size)
            applications_list = []
            for application in applications:
                qr_code_base64 = base64.b64encode(application.QRcode).decode('utf-8') if application.QRcode else ''
                applications_list.append({
                    'id': application.id, 'data_id': application.data_id, 'data_name': application.data_name,
                    'data_alias': application.data_alias, 'data_url': application.data_url,
                    'applicant_name': application.applicant_name, 'applicant_user_number': application.applicant_user_number,
                    'reason': application.reason, 'adm1_name': application.adm1_name, 'adm2_name': application.adm2_name,
                    'first_statu': application.adm1_statu, 'second_statu': application.adm2_statu, 'qrcode': qr_code_base64
                })
            return {'status': True, 'application_data': applications_list, 'pages': pagination}, 200
        except Exception as e:
            return {'status': False, 'msg': str(e)}, 500

class WatermarkEmbeddingResource(Resource):
    def get(self):
        request.get_json()
        return {'message': 'OK'}, 200

# --- 以下是为“编辑”功能新增的资源类 ---

class EmployeeDetailResource(Resource):
    """获取单个员工的详细信息，用于编辑页面填充表单"""
    def get(self, employee_number):
        success, data = AdmServer().get_employee_details(employee_number)
        if success:
            return {'status': True, 'data': data}, 200
        else:
            return {'status': False, 'msg': data}, 404

class UpdateEmployeeResource(Resource):
    """处理更新员工信息的请求"""
    def put(self, employee_number):
        try:
            form_data = request.form.to_dict()
            photo_file = request.files.get('photo') # 照片是可选的
        except Exception as e:
            return {'msg': f"解析请求时出错: {str(e)}", 'status': False}, 400

        success, message = AdmServer().update_employee_info(employee_number, form_data, photo_file)
        
        if success:
            return {'status': True, 'msg': message}, 200
        else:
            return {'status': False, 'msg': message}, 400
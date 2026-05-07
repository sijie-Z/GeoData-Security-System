import os
import logging

from flask import request, send_file, jsonify
from flask_restful import Resource

from server.emp_server import EmpServer


class EmpGetApprovedApplications(Resource):
    def get(self):
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 2))
            user_number = request.args.get('userNumber')

            get_approved_applications_server = EmpServer()
            get_applications, pagination = get_approved_applications_server.emp_get_approved_applications(page,
                                                                                                          page_size,
                                                                                                          user_number)
            emp_get_applications = [
                {
                    'application_id': emp_get_application.id,
                    'data_id': emp_get_application.data_id,
                    'data_name': emp_get_application.data_name,
                    'data_alias': emp_get_application.data_alias,
                    'data_url': emp_get_application.data_url,
                    'send_file_person_user_number': emp_get_application.adm2_user_number,
                    'applicant_name': emp_get_application.applicant_name,
                    'applicant_user_number': emp_get_application.applicant_user_number,
                }
                for emp_get_application in get_applications
            ]

            return {
                'status': True,
                'emp_get_applications': emp_get_applications,
                'pages': pagination,
            }, 200
        except Exception as e:
            logging.error(str(e))
            return {
                'status': False,
                'msg': '操作失败，请稍后重试'
            }, 500


class EmpDownloadZip(Resource):
    def post(self):
        try:
            # 获取请求中的参数
            application_id = request.json.get('application_id')
            data_id = request.json.get('data_id')
            applicant_user_number = request.json.get('applicant_user_number')
            applicant = request.json.get('applicant')
            send_file_person_user_number=request.json.get('send_file_person_user_number')




            # 获取文件路径\文件名称
            zip_path, zip_name = EmpServer().select_download_zip(application_id)

            # 检查文件是否存在
            if zip_path and os.path.exists(zip_path) and zip_name:
                # 提取文件名
                file_name = os.path.basename(zip_name)

                # 使用 send_file 发送文件，设置正确的 Content-Disposition 头
                response = send_file(zip_path, as_attachment=True)
                response.headers["Content-Disposition"] = f'attachment; filename="{file_name}"'
                return response

            # 如果文件不存在
            return jsonify({"message": "File not found."})

        except Exception as e:
            # 错误处理
            logging.error(str(e))
            return jsonify({"message": "An error occurred while processing the request."})

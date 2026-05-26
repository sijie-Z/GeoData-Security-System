from flask import request
from flask_restful import Resource
from server.appliaction_server import ApplicationServer
from extension.extension import db
from model.Application import Application


class SubmitApplicationResource(Resource):
    def post(self):
        try:
            data = request.get_json()
            application_server = ApplicationServer()
            result = application_server.submit_application(data)

            if result:
                return {
                    'status': True,
                    'msg': '提交成功'
                }, 200

            else:
                return {
                    'status': False,
                    'msg': '提交失败'

                }, 400
        except Exception as e:
            return {
                'status': False,
                'msg': str(e)
            }, 500


class EmpGetApplications(Resource):
    def get(self):
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 2))
            user_number = request.args.get('userNumber')

            get_applications_server = ApplicationServer()
            get_applications, pagination = get_applications_server.emp_get_applications(page, page_size, user_number)
            emp_get_applications = [
                {
                    'id': emp_get_application.id,
                    'data_id': emp_get_application.data_id,
                    'data_name': emp_get_application.data_name,
                    'data_alias': emp_get_application.data_alias,
                    'data_url': emp_get_application.data_url,
                    'applicant_name': emp_get_application.applicant_name,
                    'applicant_user_number': emp_get_application.applicant_user_number,
                    'reason': emp_get_application.reason,
                    'first_statu': emp_get_application.adm1_statu,
                    'second_statu': emp_get_application.adm2_statu

                }
                for emp_get_application in get_applications
            ]

            return {
                'status': True,
                'emp_get_applications': emp_get_applications,
                'pages': pagination,
            }, 200
        except Exception as e:
            return {
                'status': False,
                'msg': str(e)
            }, 500


class Adm1GetApplicationsResource(Resource):
    def get(self):
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 2))

            adm1_get_server = ApplicationServer()
            applications, pagination = adm1_get_server.get_adm1_applications(page, page_size)

            applications_list = [
                {
                    'id': application.id,
                    'data_id': application.data_id,
                    'data_name': application.data_name,
                    'data_alias': application.data_alias,
                    'data_url': application.data_url,
                    'applicant_name': application.applicant_name,
                    'applicant_user_number': application.applicant_user_number,
                    'reason': application.reason
                }
                for application in applications
            ]
            return {
                'status': True,
                'application_data': applications_list,
                'pages': pagination  # 返回分页信息
            }, 200
        except Exception as e:
            return {
                'status': False,
                'msg': str(e)
            }, 500


class Adm2GetApplicationsResource(Resource):
    def get(self):
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 2))
            adm2_get_server = ApplicationServer()
            applications, pagination = adm2_get_server.get_adm2_applications(page, page_size)
            applications_list = [
                {
                    'id': application.id,
                    'data_id': application.data_id,
                    'data_name': application.data_name,
                    'data_alias': application.data_alias,
                    'data_url': application.data_url,
                    'applicant_name': application.applicant_name,
                    'applicant_user_number': application.applicant_user_number,
                    'reason': application.reason,
                    'first_statu': application.adm1_statu,
                    'second_statu': application.adm2_statu
                }
                for application in applications
            ]
            return {
                'status': True,
                'application_data': applications_list,
                'pages': pagination  # 返回分页信息
            }, 200
        except Exception as e:
            return {
                'status': False,
                'msg': str(e)
            }, 500


class Adm1GetApproved(Resource):
    def get(self):
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 2))
            adm1_get_approved_server = ApplicationServer()
            approved_applications, pagination = adm1_get_approved_server.adm1_get_approved(page, page_size)
            approved_applications_list = [
                {
                    'id': approved_application.id,
                    'data_id': approved_application.data_id,
                    'data_name': approved_application.data_name,
                    'data_alias': approved_application.data_alias,
                    'data_url': approved_application.data_url,
                    'applicant_name': approved_application.applicant_name,
                    'applicant_user_number': approved_application.applicant_user_number,
                    'reason': approved_application.reason,
                    'first_statu': approved_application.adm1_statu,
                    'second_statu': approved_application.adm2_statu
                }
                for approved_application in approved_applications
            ]

            return {
                'status': True,
                'approved_application_data': approved_applications_list,
                'pages': pagination
            }, 200

        except Exception as e:
            return {
                'status': False,
                'msg': str(e)
            }, 500


class Adm2GetApproved(Resource):
    def get(self):
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 2))
            adm2_get_approved_server = ApplicationServer()
            approved_applications, pagination = adm2_get_approved_server.adm2_get_approved(page, page_size)
            approved_applications_list = [
                {
                    'id': approved_application.id,
                    'data_id': approved_application.data_id,
                    'data_name': approved_application.data_name,
                    'data_alias': approved_application.data_alias,
                    'data_url': approved_application.data_url,
                    'applicant_name': approved_application.applicant_name,
                    'applicant_user_number': approved_application.applicant_user_number,
                    'reason': approved_application.reason,
                    'first_statu': approved_application.adm1_statu,
                    'second_statu': approved_application.adm2_statu
                }
                for approved_application in approved_applications
            ]
            return {
                'status': True,
                'approved_application_data': approved_applications_list,
                'pages': pagination
            }, 200
        except Exception as e:
            return {
                'status': False,
                'msg': str(e)
            }, 500


class Adm1PassResource(Resource):
    def post(self):
        try:
            data = request.get_json()
            application_id = data.get('id')
            adm1_name = data.get('user_name')
            adm1_user_number = data.get('user_number')

            # Fetch the application and update its status
            application = Application.query.filter_by(id=application_id).first()
            if application and not application.adm1_approve_statu:
                application.adm1_statu = True
                application.adm1_approve_statu = True
                application.adm1_name = adm1_name
                application.adm1_user_number = adm1_user_number
                db.session.commit()
                return {'status': True, 'msg': '记录已通过'}, 200
            else:
                return {'status': False, 'msg': '无效的记录或已经审批'}, 400
        except Exception as e:
            db.session.rollback()
            return {'status': False, 'msg': str(e)}, 500


class Adm1FailResource(Resource):
    def post(self):
        try:
            data = request.get_json()
            application_id = data.get('id')
            adm1_name = data.get('user_name')
            adm1_user_number = data.get('user_number')

            # Fetch the application and update its status
            application = Application.query.filter_by(id=application_id).first()
            if application and not application.adm1_approve_statu:
                application.adm1_statu = False
                application.adm1_approve_statu = True
                application.adm1_name = adm1_name
                application.adm1_user_number = adm1_user_number
                db.session.commit()
                return {'status': True, 'msg': '记录已标记为不通过'}, 200
            else:
                return {'status': False, 'msg': '无效的记录或已经审批'}, 400
        except Exception as e:
            db.session.rollback()
            return {'status': False, 'msg': str(e)}, 500


class Adm2PassResource(Resource):
    def post(self):
        try:
            data = request.get_json()
            application_id = data.get('id')
            adm2_name = data.get('user_name')
            adm2_user_number = data.get('user_number')

            # Fetch the application and update its status
            application = Application.query.filter_by(id=application_id).first()
            if application and application.adm1_approve_statu and not application.adm2_approve_statu:
                application.adm2_statu = True
                application.adm2_approve_statu = True
                application.adm2_name = adm2_name
                application.adm2_user_number = adm2_user_number
                db.session.commit()
                return {'status': True, 'msg': '记录已通过'}, 200
            else:
                return {'status': False, 'msg': '无效的记录或已经审批'}, 400
        except Exception as e:
            db.session.rollback()
            return {'status': False, 'msg': str(e)}, 500


class Adm2FailResource(Resource):
    def post(self):
        try:
            data = request.get_json()
            application_id = data.get('id')
            adm2_name = data.get('user_name')
            adm2_user_number = data.get('user_number')

            # Fetch the application and update its status
            application = Application.query.filter_by(id=application_id).first()
            if application and application.adm1_approve_statu and not application.adm2_approve_statu:
                application.adm2_statu = False
                application.adm2_approve_statu = True
                application.adm2_name = adm2_name
                application.adm2_user_number = adm2_user_number
                db.session.commit()
                return {'status': True, 'msg': '记录已标记为不通过'}, 200
            else:
                return {'status': False, 'msg': '无效的记录或已经审批'}, 400
        except Exception as e:
            db.session.rollback()
            return {'status': False, 'msg': str(e)}, 500

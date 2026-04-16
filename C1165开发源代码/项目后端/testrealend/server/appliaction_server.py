import datetime

from extension.extension import db
from model.Application import Application
import logging

logging.basicConfig(level=logging.INFO)


class ApplicationServer:
    def submit_application(self, data):
        try:

            application_submission_time = datetime.datetime.now()

            application_submit = Application(
                data_id=data.get('data_id'),
                data_name=data.get('data_name'),
                data_alias=data.get('data_alias'),
                data_url=data.get('data_url'),
                applicant_name=data.get('applicant'),
                applicant_user_number=data.get('user_number'),
                reason=data.get('reason'),
                application_submission_time=application_submission_time,
            )
            db.session.add(application_submit)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logging.error(f'提交失败: {str(e)}')
            return False

    def emp_get_applications(self, page, page_size, user_number):
        try:
            # query = db.session.query(Application)
            query = Application.query.filter_by(applicant_user_number=user_number)
            total = query.count()

            emp_get_applications = query.offset((page - 1) * page_size).limit(page_size).all()
            pagination = {
                'has_next': page * page_size < total,
                'has_previous': page > 1,
                'next': page + 1 if page * page_size < total else None,
                'page': page,
                'page_size': page_size,
                'pages': (total + page_size - 1) // page_size,
                'previous': page - 1 if page > 1 else None,
                'total': total
            }
            return emp_get_applications, pagination
        except Exception as e:
            db.session.rollback()
            logging.error(e)
            return [], None

    def get_adm1_applications(self, page, page_size):
        try:
            query = Application.query.filter_by(adm1_statu=None)
            total = query.count()  # 获取总记录数
            # 应用分页
            applications = query.offset((page - 1) * page_size).limit(page_size).all()
            pagination = {
                'has_next': page * page_size < total,
                'has_previous': page > 1,
                'next': page + 1 if page * page_size < total else None,
                'page': page,
                'page_size': page_size,
                'pages': (total + page_size - 1) // page_size,
                'previous': page - 1 if page > 1 else None,
                'total': total
            }
            return applications, pagination
        except Exception as e:
            db.session.rollback()
            logging.error(e)
            return [], None  # 在出现异常时返回空列表和空分页信息

    def get_adm2_applications(self, page, page_size):
        try:
            query = Application.query.filter_by(adm1_approve_statu=True, adm1_statu=True, adm2_approve_statu=None)
            total = query.count()  # 获取总记录数
            # 应用分页
            applications = query.offset((page - 1) * page_size).limit(page_size).all()
            pagination = {
                'has_next': page * page_size < total,
                'has_previous': page > 1,
                'next': page + 1 if page * page_size < total else None,
                'page': page,
                'page_size': page_size,
                'pages': (total + page_size - 1) // page_size,
                'previous': page - 1 if page > 1 else None,
                'total': total
            }
            return applications, pagination
        except Exception as e:
            db.session.rollback()
            logging.error(e)
            return [], None  # 在出现异常时返回空列表和空分页信息

    def adm1_get_approved(self, page, page_size):
        try:
            query = Application.query.filter_by(adm1_approve_statu=True)
            total = query.count()
            applications = query.offset((page - 1) * page_size).limit(page_size).all()
            pagination = {
                'has_next': page * page_size < total,
                'has_previous': page > 1,
                'next': page + 1 if page * page_size < total else None,
                'page': page,
                'page_size': page_size,
                'pages': (total + page_size - 1) // page_size,
                'previous': page - 1 if page > 1 else None,
                'total': total
            }
            # print(applications)
            return applications, pagination
        except Exception as e:
            db.session.rollback()
            logging.error(e)
            return [], None

    def adm2_get_approved(self, page, page_size):
        try:
            query = Application.query.filter_by(adm2_approve_statu=True)
            total = query.count()
            applications = query.offset((page - 1) * page_size).limit(page_size).all()
            pagination = {
                'has_next': page * page_size < total,
                'has_previous': page > 1,
                'next': page + 1 if page * page_size < total else None,
                'page': page,
                'page_size': page_size,
                'pages': (total + page_size - 1) // page_size,
                'previous': page - 1 if page > 1 else None,
                'total': total
            }
            return applications, pagination
        except Exception as e:
            db.session.rollback()
            logging.error(e)
            return [], None

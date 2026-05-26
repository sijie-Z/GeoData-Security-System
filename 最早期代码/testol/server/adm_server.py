import logging

# from sqlalchemy import func

from extension.extension import db
from model.Application import Application

from model.Employee_Info import EmployeeInfo


class AdmServer:
    def get_emp_info_list(self):
        emp_info_list = db.session.query(EmployeeInfo).all()
        num_emp_info = len(emp_info_list)
        return emp_info_list, num_emp_info

    def get_employee_photo(self, employee_number):
        employee = EmployeeInfo.query.filter_by(employee_number=employee_number).first()
        if employee:
            return employee.face_photo
        return None

    def applications_generate_watermark(self, page, page_size):
        try:
            query = Application.query.filter_by(adm1_statu=True, adm2_statu=True)
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

    def embedding_watermark_application(self, page, page_size):
        try:
            query = Application.query.filter_by(adm1_statu=True, adm2_statu=True).filter(Application.QRcode !=None)
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

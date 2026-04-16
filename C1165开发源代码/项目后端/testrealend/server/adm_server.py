# import logging

# # from sqlalchemy import func

# from extension.extension import db
# from model.Application import Application

# from model.Employee_Info import EmployeeInfo


# class AdmServer:
#     def get_emp_info_list(self):
#         emp_info_list = db.session.query(EmployeeInfo).all()
#         num_emp_info = len(emp_info_list)
#         return emp_info_list, num_emp_info

#     def get_employee_photo(self, employee_number):
#         employee = EmployeeInfo.query.filter_by(employee_number=employee_number).first()
#         if employee:
#             return employee.face_photo
#         return None

#     def applications_generate_watermark(self, page, page_size):
#         try:
#             query = Application.query.filter_by(adm1_statu=True, adm2_statu=True)
#             total = query.count()  # 获取总记录数
#             # 应用分页
#             applications = query.offset((page - 1) * page_size).limit(page_size).all()
#             pagination = {
#                 'has_next': page * page_size < total,
#                 'has_previous': page > 1,
#                 'next': page + 1 if page * page_size < total else None,
#                 'page': page,
#                 'page_size': page_size,
#                 'pages': (total + page_size - 1) // page_size,
#                 'previous': page - 1 if page > 1 else None,
#                 'total': total
#             }
#             return applications, pagination
#         except Exception as e:
#             db.session.rollback()
#             logging.error(e)
#             return [], None  # 在出现异常时返回空列表和空分页信息

#     def embedding_watermark_application(self, page, page_size):
#         try:
#             query = Application.query.filter_by(adm1_statu=True, adm2_statu=True).filter(Application.QRcode !=None)
#             total = query.count()  # 获取总记录数
#             # 应用分页
#             applications = query.offset((page - 1) * page_size).limit(page_size).all()
#             pagination = {
#                 'has_next': page * page_size < total,
#                 'has_previous': page > 1,
#                 'next': page + 1 if page * page_size < total else None,
#                 'page': page,
#                 'page_size': page_size,
#                 'pages': (total + page_size - 1) // page_size,
#                 'previous': page - 1 if page > 1 else None,
#                 'total': total
#             }
#             return applications, pagination
#         except Exception as e:
#             db.session.rollback()
#             logging.error(e)
#             return [], None  # 在出现异常时返回空列表和空分页信息


# d:\Desktop\ESRI_test\testrealend\server\adm_server.py
# d:\Desktop\ESRI_test\testrealend\server\adm_server.py

# import logging
# from model.Application import Application
# from model.Employee_Info import EmployeeInfo
# from model.Employee_Account import EmployeeAccount
# from extension.extension import db
# from sqlalchemy import or_
# from werkzeug.security import generate_password_hash

# class AdmServer:
#     def get_emp_info_list(self):
#         emp_info_list = db.session.query(EmployeeInfo).all()
#         return emp_info_list, len(emp_info_list)

#     def get_employee_photo(self, employee_number):
#         # 照片查询逻辑保持不变，因为它用的是正确的 employee_number
#         employee = EmployeeInfo.query.filter_by(employee_number=employee_number).first()
#         if employee and employee.face_photo:
#             return employee.face_photo
#         return None
    
#     def delete_employee(self, employee_number: str):
#         # 删除逻辑也保持不变，因为它用的是正确的 employee_number
#         employee_info = EmployeeInfo.query.filter_by(employee_number=employee_number).first()
#         if not employee_info:
#             return False, "未找到该员工"
#         employee_account = EmployeeAccount.query.filter_by(employee_number=employee_number).first()
#         try:
#             if employee_account:
#                 db.session.delete(employee_account)
#             db.session.delete(employee_info)
#             db.session.commit()
#             return True, f"员工 {employee_info.name} 已成功删除"
#         except Exception as e:
#             db.session.rollback()
#             logging.error(f'删除员工失败: {str(e)}')
#             return False, "删除失败，数据库错误"

#     # 【最终修复】完全适配你的数据库结构和前端表单
#     def add_employee_with_photo(self, form_data, photo_file):
#         job_number = form_data.get('job_number')
#         employee_number_from_form = form_data.get('employee_number') # 从表单获取员工编号

#         # 预检查，使用 job_number 和 employee_number 进行唯一性检查
#         if EmployeeInfo.query.filter_by(job_number=job_number).first():
#             return False, "该工号已被注册"
#         if EmployeeInfo.query.filter_by(employee_number=employee_number_from_form).first():
#             return False, "该员工编号已存在"
        
#         photo_binary_data = photo_file.read() if photo_file else None

#         # 创建 EmployeeInfo 对象，不传入 id，让数据库自增
#         new_employee_info = EmployeeInfo(
#             employee_number=employee_number_from_form, # 使用表单填写的员工编号
#             name=form_data.get('name'),
#             job_number=job_number,
#             id_number=form_data.get('id_number'), # id_number 来自 parser 的默认值或空
#             phone_number=form_data.get('phone_number'),
#             address=form_data.get('address'),
#             face_photo=photo_binary_data
#         )

#         # 为新员工创建一个账户，使用默认密码 '123456'
#         new_employee_account = EmployeeAccount(
#             employee_user_name=job_number,  # 登录名使用工号
#             employee_user_password=generate_password_hash('123456'), # 设置默认密码
#             employee_number=employee_number_from_form # 外键关联
#         )
        
#         try:
#             # 使用分两次提交的可靠方法
#             db.session.add(new_employee_info)
#             db.session.commit()

#             db.session.add(new_employee_account)
#             db.session.commit()
            
#             return True, "新员工添加成功"
#         except Exception as e:
#             db.session.rollback()
#             # 尝试删除可能已创建的 employee_info，保持数据一致性
#             created_info = EmployeeInfo.query.filter_by(employee_number=employee_number_from_form).first()
#             if created_info:
#                 db.session.delete(created_info)
#                 db.session.commit()
#             logging.error(f'添加新员工失败: {str(e)}')
#             # 将详细的数据库错误信息返回，方便调试
#             return False, f"添加失败: 数据库操作错误 - {str(e)}"
    
#     def applications_generate_watermark(self, page, page_size):
#         try:
#             query = Application.query.filter_by(adm1_statu=True, adm2_statu=True)
#             total = query.count()
#             applications = query.offset((page - 1) * page_size).limit(page_size).all()
#             pagination = {'has_next': page * page_size < total, 'has_previous': page > 1, 'next': page + 1 if page * page_size < total else None, 'page': page, 'page_size': page_size, 'pages': (total + page_size - 1) // page_size, 'previous': page - 1 if page > 1 else None, 'total': total}
#             return applications, pagination
#         except Exception as e:
#             db.session.rollback()
#             logging.error(e)
#             return [], None

#     def embedding_watermark_application(self, page, page_size):
#         try:
#             query = Application.query.filter_by(adm1_statu=True, adm2_statu=True).filter(Application.QRcode != None)
#             total = query.count()
#             applications = query.offset((page - 1) * page_size).limit(page_size).all()
#             pagination = {'has_next': page * page_size < total, 'has_previous': page > 1, 'next': page + 1 if page * page_size < total else None, 'page': page, 'page_size': page_size, 'pages': (total + page_size - 1) // page_size, 'previous': page - 1 if page > 1 else None, 'total': total}
#             return applications, pagination
#         except Exception as e:
#             db.session.rollback()
#             logging.error(e)
#             return [], None

# d:\Desktop\ESRI_test\testrealend\server\adm_server.py

import logging
from model.Application import Application
from model.Employee_Info import EmployeeInfo
from model.Employee_Account import EmployeeAccount
from extension.extension import db
from sqlalchemy import or_
from werkzeug.security import generate_password_hash

class AdmServer:
    # --- 你所有已有的方法，保持100%不变 ---
    def get_emp_info_list(self):
        emp_info_list = db.session.query(EmployeeInfo).all()
        return emp_info_list, len(emp_info_list)

    def get_employee_photo(self, employee_number):
        employee = EmployeeInfo.query.filter_by(employee_number=employee_number).first()
        if employee and employee.face_photo:
            return employee.face_photo
        return None
    
    def delete_employee(self, employee_number: str):
        employee_info = EmployeeInfo.query.filter_by(employee_number=employee_number).first()
        if not employee_info:
            return False, "未找到该员工"
        employee_account = EmployeeAccount.query.filter_by(employee_number=employee_number).first()
        try:
            if employee_account:
                db.session.delete(employee_account)
            db.session.delete(employee_info)
            db.session.commit()
            return True, f"员工 {employee_info.name} 已成功删除"
        except Exception as e:
            db.session.rollback()
            logging.error(f'删除员工失败: {str(e)}')
            return False, "删除失败，数据库错误"

    def add_employee_with_photo(self, form_data, photo_file):
        job_number = form_data.get('job_number')
        employee_number_from_form = form_data.get('employee_number')
        if EmployeeInfo.query.filter_by(job_number=job_number).first():
            return False, "该工号已被注册"
        if EmployeeInfo.query.filter_by(employee_number=employee_number_from_form).first():
            return False, "该员工编号已存在"
        photo_binary_data = photo_file.read() if photo_file else None
        new_employee_info = EmployeeInfo(
            employee_number=employee_number_from_form, name=form_data.get('name'),
            job_number=job_number, id_number=form_data.get('id_number'),
            phone_number=form_data.get('phone_number'), address=form_data.get('address'),
            face_photo=photo_binary_data
        )
        new_employee_account = EmployeeAccount(
            employee_user_name=job_number,
            employee_user_password=generate_password_hash('123456'),
            employee_number=employee_number_from_form
        )
        try:
            db.session.add(new_employee_info)
            db.session.commit()
            db.session.add(new_employee_account)
            db.session.commit()
            return True, "新员工添加成功"
        except Exception as e:
            db.session.rollback()
            created_info = EmployeeInfo.query.filter_by(employee_number=employee_number_from_form).first()
            if created_info:
                db.session.delete(created_info)
                db.session.commit()
            logging.error(f'添加新员工失败: {str(e)}')
            return False, f"添加失败: 数据库操作错误 - {str(e)}"
    
    def applications_generate_watermark(self, page, page_size):
        # ... 保持不变
        try:
            query = Application.query.filter_by(adm1_statu=True, adm2_statu=True)
            total = query.count()
            applications = query.offset((page - 1) * page_size).limit(page_size).all()
            pagination = {'has_next': page * page_size < total, 'has_previous': page > 1, 'next': page + 1 if page * page_size < total else None, 'page': page, 'page_size': page_size, 'pages': (total + page_size - 1) // page_size, 'previous': page - 1 if page > 1 else None, 'total': total}
            return applications, pagination
        except Exception as e:
            db.session.rollback()
            logging.error(e)
            return [], None

    def embedding_watermark_application(self, page, page_size):
        # ... 保持不变
        try:
            query = Application.query.filter_by(adm1_statu=True, adm2_statu=True).filter(Application.QRcode != None)
            total = query.count()
            applications = query.offset((page - 1) * page_size).limit(page_size).all()
            pagination = {'has_next': page * page_size < total, 'has_previous': page > 1, 'next': page + 1 if page * page_size < total else None, 'page': page, 'page_size': page_size, 'pages': (total + page_size - 1) // page_size, 'previous': page - 1 if page > 1 else None, 'total': total}
            return applications, pagination
        except Exception as e:
            db.session.rollback()
            logging.error(e)
            return [], None

    # --- 以下是为“编辑”功能新增的方法 ---

    def get_employee_details(self, employee_number: str):
        """根据员工编号获取员工详细信息"""
        employee = EmployeeInfo.query.filter_by(employee_number=employee_number).first()
        if not employee:
            return False, "未找到该员工"
        
        details = {
            "employee_number": employee.employee_number,
            "name": employee.name,
            "job_number": employee.job_number,
            "id_number": employee.id_number,
            "phone_number": employee.phone_number,
            "address": employee.address,
            "has_photo": True if employee.face_photo else False
        }
        return True, details

    def update_employee_info(self, employee_number: str, form_data, photo_file):
        """更新员工信息"""
        employee = EmployeeInfo.query.filter_by(employee_number=employee_number).first()
        if not employee:
            return False, "未找到要更新的员工"

        try:
            # 更新文本字段
            employee.name = form_data.get('name', employee.name)
            employee.job_number = form_data.get('job_number', employee.job_number)
            employee.id_number = form_data.get('id_number', employee.id_number)
            employee.phone_number = form_data.get('phone_number', employee.phone_number)
            employee.address = form_data.get('address', employee.address)

            # 如果上传了新照片，则更新照片
            if photo_file:
                employee.face_photo = photo_file.read()

            db.session.commit()
            return True, "员工信息更新成功"
        except Exception as e:
            db.session.rollback()
            logging.error(f'更新员工信息失败: {str(e)}')
            return False, f"更新失败: 数据库错误 - {str(e)}"
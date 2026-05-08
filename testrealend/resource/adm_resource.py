from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from model.Employee_Info import EmployeeInfo
from model.Employee_Account import EmployeeAccount
from extension.extension import db
from utils.required import admin_required
import logging

class GetEmpInfoListResource(Resource):
    @admin_required
    def get(self):
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        
        pagination = EmployeeInfo.query.paginate(page=page, per_page=page_size, error_out=False)
        
        data_list = []
        for emp in pagination.items:
            data_list.append({
                'employee_number': emp.employee_number,
                'name': emp.name,
                'job_number': emp.job_number,
                'address': emp.address,
                'phone_number': emp.phone_number,
                'photo_url': f'/api/employee/photo/{emp.employee_number}'
            })
            
        return {
            'status': True,
            'msg': '记录获取成功',
            'data': {
                'list': data_list,
                'rows': pagination.total
            }
        }, 200

class GetEmpPhotoResource(Resource):
    def get(self, employee_number):
        # Already implemented in profile_resource.py
        # Keeping here for compatibility if needed
        pass


class AddEmployeeResource(Resource):
    @admin_required
    def post(self):
        try:
            employee_number = (request.form.get('employee_number') or '').strip()
            name = (request.form.get('name') or '').strip()
            job_number = (request.form.get('job_number') or '').strip()
            id_number = (request.form.get('id_number') or '').strip()
            phone_number = (request.form.get('phone_number') or '').strip()
            address = (request.form.get('address') or '').strip()
            password = (request.form.get('password') or '').strip()
            photo = request.files.get('photo')

            if not all([employee_number, name, job_number, id_number, phone_number, address, password]):
                return {'status': False, 'msg': '缺少必填字段'}, 400

            if EmployeeInfo.query.filter_by(employee_number=employee_number).first():
                return {'status': False, 'msg': '员工编号已存在'}, 400
            if EmployeeInfo.query.filter_by(job_number=job_number).first():
                return {'status': False, 'msg': '工号已存在'}, 400
            if EmployeeInfo.query.filter_by(id_number=id_number).first():
                return {'status': False, 'msg': '身份证号已存在'}, 400
            if EmployeeInfo.query.filter_by(phone_number=phone_number).first():
                return {'status': False, 'msg': '手机号已存在'}, 400
            if EmployeeAccount.query.filter_by(employee_user_name=employee_number).first():
                return {'status': False, 'msg': '登录用户名已存在'}, 400

            new_info = EmployeeInfo(
                employee_number=employee_number,
                name=name,
                job_number=job_number,
                id_number=id_number,
                phone_number=phone_number,
                address=address,
                face_photo=photo.read() if photo else None
            )
            from werkzeug.security import generate_password_hash
            new_account = EmployeeAccount(
                employee_user_name=employee_number,
                employee_user_password=generate_password_hash(password),
                employee_number=employee_number,
                role='employee'
            )
            db.session.add(new_info)
            db.session.add(new_account)
            db.session.commit()
            return {'status': True, 'msg': '员工添加成功'}, 201
        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '操作失败，请稍后重试'}, 500


class EmployeeDetailsResource(Resource):
    @jwt_required()
    def get(self, employee_number):
        item = EmployeeInfo.query.filter_by(employee_number=employee_number).first()
        if not item:
            return {'status': False, 'msg': '员工不存在'}, 404
        return {
            'status': True,
            'data': {
                'employee_number': item.employee_number,
                'name': item.name,
                'job_number': item.job_number,
                'id_number': item.id_number,
                'phone_number': item.phone_number,
                'address': item.address,
                'has_photo': bool(item.face_photo)
            }
        }, 200


class EmployeeUpdateResource(Resource):
    @admin_required
    def put(self, employee_number):
        try:
            item = EmployeeInfo.query.filter_by(employee_number=employee_number).first()
            if not item:
                return {'status': False, 'msg': '员工不存在'}, 404

            name = request.form.get('name')
            job_number = request.form.get('job_number')
            id_number = request.form.get('id_number')
            phone_number = request.form.get('phone_number')
            address = request.form.get('address')
            photo = request.files.get('photo')

            if name is not None:
                item.name = name.strip()
            if job_number is not None:
                target = job_number.strip()
                dup = EmployeeInfo.query.filter(EmployeeInfo.job_number == target, EmployeeInfo.employee_number != employee_number).first()
                if dup:
                    return {'status': False, 'msg': '工号已存在'}, 400
                item.job_number = target
            if id_number is not None:
                target = id_number.strip()
                dup = EmployeeInfo.query.filter(EmployeeInfo.id_number == target, EmployeeInfo.employee_number != employee_number).first()
                if dup:
                    return {'status': False, 'msg': '身份证号已存在'}, 400
                item.id_number = target
            if phone_number is not None:
                target = phone_number.strip()
                dup = EmployeeInfo.query.filter(EmployeeInfo.phone_number == target, EmployeeInfo.employee_number != employee_number).first()
                if dup:
                    return {'status': False, 'msg': '手机号已存在'}, 400
                item.phone_number = target
            if address is not None:
                item.address = address.strip()
            if photo:
                item.face_photo = photo.read()

            db.session.commit()
            return {'status': True, 'msg': '员工信息更新成功'}, 200
        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '操作失败，请稍后重试'}, 500


class AdminDeleteEmployeeResource(Resource):
    @admin_required
    def delete(self, employee_number):
        try:
            info = EmployeeInfo.query.filter_by(employee_number=employee_number).first()
            if not info:
                return {'status': False, 'message': '员工不存在'}, 404
            account = EmployeeAccount.query.filter_by(employee_number=employee_number).first()
            if account:
                db.session.delete(account)
            db.session.delete(info)
            db.session.commit()
            return {'status': True, 'message': '删除成功'}, 200
        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'message': '操作失败，请稍后重试'}, 500


class AccountCreateResource(Resource):
    @admin_required
    def post(self):
        try:
            data = request.get_json() or {}
            employee_number = (data.get('employee_number') or '').strip()
            username = (data.get('username') or '').strip()
            password = (data.get('password') or '').strip()

            if not employee_number or not username or not password:
                return {'status': False, 'msg': '缺少必填字段'}, 400

            # 兼容前端 ADMIN/USER 的取值；当前该入口创建员工账号。
            role_raw = (data.get('role') or 'USER').strip().upper()
            account_role = 'employee' if role_raw in ['USER', 'ADMIN'] else 'employee'

            emp = EmployeeInfo.query.filter_by(employee_number=employee_number).first()
            if not emp:
                return {'status': False, 'msg': '关联员工不存在'}, 404

            if EmployeeAccount.query.filter_by(employee_user_name=username).first():
                return {'status': False, 'msg': '账号名称已存在'}, 400

            if EmployeeAccount.query.filter_by(employee_number=employee_number).first():
                return {'status': False, 'msg': '该员工已存在登录账号'}, 400

            from werkzeug.security import generate_password_hash
            account = EmployeeAccount(
                employee_user_name=username,
                employee_user_password=generate_password_hash(password),
                employee_number=employee_number,
                role=account_role
            )
            db.session.add(account)
            db.session.commit()
            return {'status': True, 'msg': '账号创建成功'}, 201
        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '操作失败，请稍后重试'}, 500

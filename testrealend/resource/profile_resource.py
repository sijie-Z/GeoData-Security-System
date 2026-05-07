from flask import request, send_file
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from model.Employee_Info import EmployeeInfo
from model.Employee_Account import EmployeeAccount
from extension.extension import db, limiter
from werkzeug.security import check_password_hash, generate_password_hash
import io
import os

class EmployeeProfileResource(Resource):
    @jwt_required()
    def get(self):
        identity = get_jwt_identity()
        user_number = identity.get('number')
        user = EmployeeInfo.query.filter_by(employee_number=user_number).first()
        if user:
            return {
                'status': True,
                'data': {
                    'userName': user.name,
                    'userNumber': user.employee_number,
                    'department': user.department or '研发部',
                    'email': user.email or (user.name + '@company.com'),
                    'phoneNumber': user.phone_number,
                    'hireDate': user.hire_date.strftime('%Y-%m-%d') if user.hire_date else '2024-01-01',
                    'address': user.address,
                    'lastLoginTime': user.last_login_time.strftime('%Y-%m-%d %H:%M:%S') if user.last_login_time else '今天'
                }
            }, 200
        return {'status': False, 'msg': '用户未找到'}, 404

    @jwt_required()
    def put(self):
        identity = get_jwt_identity()
        user_number = identity.get('number')
        user = EmployeeInfo.query.filter_by(employee_number=user_number).first()
        if not user:
            return {'status': False, 'msg': '用户未找到'}, 404

        # Form data (multipart/form-data)
        user.name = request.form.get('userName', user.name)
        user.email = request.form.get('email', user.email)
        user.phone_number = request.form.get('phoneNumber', user.phone_number)
        user.address = request.form.get('address', user.address)

        avatar = request.files.get('avatar')
        if avatar:
            user.face_photo = avatar.read()

        db.session.commit()
        return {'status': True, 'msg': '资料更新成功'}, 200

class EmployeePhotoResource(Resource):
    @jwt_required()
    def get(self, employee_number):
        user = EmployeeInfo.query.filter_by(employee_number=employee_number).first()
        if user and user.face_photo:
            return send_file(io.BytesIO(user.face_photo), mimetype='image/jpeg')
        return {'status': False, 'msg': '未设置头像'}, 404

class EmployeePasswordResource(Resource):
    @jwt_required()
    @limiter.limit("5 per minute")
    def put(self):
        identity = get_jwt_identity()
        user_number = identity.get('number')
        data = request.get_json()
        old_password = (data.get('old_password') or '').strip()
        new_password = (data.get('new_password') or '').strip()

        if not new_password or len(new_password) < 6:
            return {'status': False, 'msg': '新密码长度至少6位'}, 400

        user_acc = EmployeeAccount.query.filter_by(employee_number=user_number).first()
        if not user_acc:
            return {'status': False, 'msg': '用户不存在'}, 400

        stored = user_acc.employee_user_password
        matched = check_password_hash(stored, old_password)
        if not matched and not stored.startswith(('pbkdf2:', 'sha$', '$2b$', '$2a$')):
            # Legacy plaintext auto-upgrade on password change
            if stored != old_password:
                return {'status': False, 'msg': '原密码错误'}, 400

        if not matched and stored.startswith(('pbkdf2:', 'sha$', '$2b$', '$2a$')):
            return {'status': False, 'msg': '原密码错误'}, 400

        user_acc.employee_user_password = generate_password_hash(new_password)
        db.session.commit()
        return {'status': True, 'msg': '密码修改成功'}, 200

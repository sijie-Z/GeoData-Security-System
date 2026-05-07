from flask import request
from flask_restful import Resource
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    verify_jwt_in_request,
    decode_token,
)
from extension.extension import db
from model.Employee_Account import EmployeeAccount
from model.Employee_Info import EmployeeInfo
from model.Adm_Account import AdmAccount
from model.Adm_Info import AdmInfo
from extension.extension import limiter
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from utils.log_helper import log_action
import logging


def _password_matches(stored_password, input_password):
    """Check password. Returns (ok, new_hash_or_none) where new_hash is set
    when a legacy plaintext password needs upgrading."""
    if not stored_password or not input_password:
        return False, None
    try:
        if check_password_hash(stored_password, input_password):
            return True, None
    except Exception:
        pass
    # Auto-upgrade legacy plaintext passwords
    if not stored_password.startswith(('pbkdf2:', 'sha$', '$2b$', '$2a$')):
        if stored_password == input_password:
            from werkzeug.security import generate_password_hash
            return True, generate_password_hash(input_password)
        return False, None
    return False, None

class LoginResource(Resource):
    """
    用户登录
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [username, password, role]
          properties:
            username: {type: string, description: 用户名}
            password: {type: string, description: 密码}
            role: {type: string, enum: [employee, admin], description: 角色}
    responses:
      200: {description: 登录成功}
      401: {description: 用户名或密码错误}
    """
    @limiter.limit("10 per minute")
    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        role_type = data.get('role') # 'employee' or 'admin'
        
        if role_type == 'admin':
            user = AdmAccount.query.filter_by(adm_user_name=username).first()
            if user:
                ok, new_hash = _password_matches(user.adm_user_password, password)
                if ok:
                    if new_hash:
                        user.adm_user_password = new_hash
                    access_token = create_access_token(identity={'username': username, 'role': user.role, 'number': user.adm_number})
                    refresh_token = create_refresh_token(identity={'username': username, 'role': user.role, 'number': user.adm_number})

                    # Update last login
                    adm_info = AdmInfo.query.filter_by(adm_number=user.adm_number).first()
                    if adm_info:
                        adm_info.last_login_time = datetime.utcnow()
                    db.session.commit()

                    log_action(user.adm_number, username, '登录', '成功', 'admin')

                    return {
                        'status': True,
                        'user_number': user.adm_number,
                        'role': user.role,
                        'access_token': access_token,
                        'refresh_token': refresh_token,
                        'user_name': username,
                        'permissions': ['*'] # Admin has all permissions
                    }, 200
        else:
            user = EmployeeAccount.query.filter_by(employee_user_name=username).first()
            if user:
                ok, new_hash = _password_matches(user.employee_user_password, password)
                if ok:
                    if new_hash:
                        user.employee_user_password = new_hash
                    access_token = create_access_token(identity={'username': username, 'role': 'employee', 'number': user.employee_number})
                    refresh_token = create_refresh_token(identity={'username': username, 'role': 'employee', 'number': user.employee_number})

                    # Update last login
                    emp_info = EmployeeInfo.query.filter_by(employee_number=user.employee_number).first()
                    if emp_info:
                        emp_info.last_login_time = datetime.utcnow()
                    db.session.commit()

                    log_action(user.employee_number, username, '登录', '成功', 'employee')

                    return {
                        'status': True,
                        'user_number': user.employee_number,
                        'role': 'employee',
                        'access_token': access_token,
                        'refresh_token': refresh_token,
                        'user_name': username,
                        'permissions': ['view', 'apply', 'download']
                    }, 200

        log_action('unknown', username or 'unknown', '登录', '失败', f'role={role_type}')
        return {'status': False, 'msg': '用户名或密码错误', 'message': '用户名或密码错误'}, 401

class RegisterResource(Resource):
    """
    员工注册
    ---
    tags: [Auth]
    consumes: [multipart/form-data]
    parameters:
      - in: formData
        name: name
        type: string
        required: true
        description: 员工姓名
      - in: formData
        name: employeeId
        type: string
        required: true
        description: 员工编号
      - in: formData
        name: idNumber
        type: string
        description: 身份证号
      - in: formData
        name: phone
        type: string
        description: 手机号
      - in: formData
        name: password
        type: string
        required: true
        description: 密码
      - in: formData
        name: avatar
        type: file
        description: 头像
    responses:
      201: {description: 注册成功}
      400: {description: 员工编号已存在}
    """
    @limiter.limit("5 per minute")
    def post(self):
        # Multipart form data
        name = request.form.get('name')
        employee_id = request.form.get('employeeId')
        id_number = request.form.get('idNumber')
        phone = request.form.get('phone')
        password = request.form.get('password')
        avatar = request.files.get('avatar')
        
        # Check if already exists
        if EmployeeInfo.query.filter_by(employee_number=employee_id).first():
            return {'status': False, 'msg': '员工编号已存在'}, 400
            
        # Create Info
        new_info = EmployeeInfo(
            employee_number=employee_id,
            name=name,
            job_number=employee_id,
            id_number=id_number,
            phone_number=phone,
            address='未填写',
            create_time=datetime.utcnow(),
            face_photo=avatar.read() if avatar else None
        )
        
        # Create Account
        new_account = EmployeeAccount(
            employee_user_name=employee_id,
            employee_user_password=generate_password_hash(password),
            employee_number=employee_id,
            role='employee'
        )
        
        try:
            db.session.add(new_info)
            db.session.flush()
            db.session.add(new_account)
            db.session.commit()
            return {'status': True, 'msg': '注册成功', 'message': '注册成功'}, 201
        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '操作失败，请稍后重试', 'message': '操作失败，请稍后重试'}, 500

class LogoutResource(Resource):
    @jwt_required()
    def post(self):
        return {'status': True, 'msg': '登出成功'}, 200

class RefreshTokenResource(Resource):
    """
    刷新访问令牌
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            refresh_token: {type: string, description: 刷新令牌}
    responses:
      200: {description: 刷新成功}
      401: {description: 令牌无效或过期}
    """
    def post(self):
        identity = None

        # 兼容两种刷新方式：
        # 1) Authorization: Bearer <refresh_token>
        # 2) JSON body: {"refresh_token": "..."}
        try:
            verify_jwt_in_request(refresh=True)
            identity = get_jwt_identity()
        except Exception:
            data = request.get_json(silent=True) or {}
            refresh_token = data.get('refresh_token')
            if not refresh_token:
                return {'status': False, 'msg': '缺少 refresh_token', 'message': '缺少 refresh_token'}, 401
            try:
                decoded = decode_token(refresh_token)
                if decoded.get('type') != 'refresh':
                    return {'status': False, 'msg': 'refresh_token 无效', 'message': 'refresh_token 无效'}, 401
                identity = decoded.get('sub')
            except Exception:
                return {'status': False, 'msg': 'refresh_token 无效或已过期', 'message': 'refresh_token 无效或已过期'}, 401

        if not identity:
            return {'status': False, 'msg': '无法解析用户身份', 'message': '无法解析用户身份'}, 401

        access_token = create_access_token(identity=identity)
        refresh_token = create_refresh_token(identity=identity)
        return {
            'status': True,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'msg': '刷新成功',
            'message': '刷新成功'
        }, 200

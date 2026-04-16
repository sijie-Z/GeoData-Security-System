# from flask_restful import Resource
# from flask import request, jsonify
# from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, create_access_token

# from extension.extension import limiter
# from model.Adm_Info import AdmInfo
# from model.Employee_Info import EmployeeInfo
# from server.common_server import CommonServer
# import logging
# from server.common_server import CommonServer
# logger = logging.getLogger(__name__)

# class RegisterResource(Resource):
#     def post(self):
#         data = request.json
#         # 前端传递的字段映射
#         name = data.get('name')
#         employee_number = data.get('employeeId')  # 工号作为employee_number
#         id_number = data.get('idNumber')
#         phone_number = data.get('phone')
#         password = data.get('password')
#         confirm_password = data.get('confirmPassword')

#         # 基础验证
#         if not all([name, employee_number, id_number, phone_number, password, confirm_password]):
#             return {'message': '所有字段均为必填'}, 400
#         if password != confirm_password:
#             return {'message': '两次输入的密码不一致'}, 400

#         # 调用注册逻辑
#         result = CommonServer.register_employee(
#             name=name,
#             employee_number=employee_number,
#             id_number=id_number,
#             phone_number=phone_number,
#             password=password
#         )

#         if result['status']:
#             return {'message': '注册成功'}, 201
#         else:
#             return {'message': result['message']}, 400

# class LoginResource(Resource):
#     def post(self):
#         data = request.json
#         username = data.get('username')
#         password = data.get('password')
#         role = data.get('role')

#         logger.info(f"登录尝试: 用户名={username}, 角色={role}")

#         user = CommonServer.authenticate_user(username, password, role)
#         if not user:
#             logger.error(f"登录失败: 用户名={username}, 角色={role}")
#             return {'message': '用户名或密码错误'}, 401

#         access_token, refresh_token = CommonServer.generate_tokens(
#             user.adm_number if role == 'admin' else user.employee_number,
#             role
#         )

#         if role == 'admin':
#             user_info = AdmInfo.query.filter_by(adm_number=user.adm_number).first()
#         else:
#             user_info = EmployeeInfo.query.filter_by(employee_number=user.employee_number).first()

#         user_name = user_info.name if user_info else '未知用户'

#         logger.info(f"登录成功: 用户名={username}, 角色={role}")
#         return {
#             'access_token': access_token,
#             'refresh_token': refresh_token,
#             'permissions': [p.name for p in user.permissions] if hasattr(user, 'permissions') else [],
#             'role': role,
#             'user_number': user.adm_number if role == 'admin' else user.employee_number,
#             'user_name': user_name
#         }, 200


# class LogoutResource(Resource):
#     @jwt_required()
#     def post(self):
#         jti = get_jwt()['jti']
#         CommonServer.add_token_to_blocklist(jti)
#         return {'message': '成功注销'}, 200


# class ProtectResource(Resource):
#     @jwt_required()
#     def get(self):
#         current_user_id = get_jwt_identity()
#         jwt_data = get_jwt()
#         role = jwt_data['role']
#         user = CommonServer.get_user(current_user_id, role)

#         if not user:
#             return {'message': '用户不存在'}, 404

#         return {
#             'message': f'欢迎, {user.adm_user_name if role == "admin" else user.employee_user_name}!',
#             'role': role,
#             'user_number': current_user_id
#         }, 200


# class RefreshTokenResource(Resource):
#     @jwt_required(refresh=True)
#     def post(self):
#         current_user_id = get_jwt_identity()
#         jti = get_jwt()['jti']

#         if CommonServer.token_in_blocklist(jti):
#             return {'message': '刷新令牌已被撤销'}, 401

#         role = request.json.get('role')
#         if not role:
#             return {'message': '需要提供角色'}, 400

#         access_token, refresh_token = CommonServer.generate_tokens(current_user_id, role)
#         return jsonify({
#             'access_token': access_token,
#             'refresh_token': refresh_token
#         }), 200


# from flask_restful import Resource
# from flask import request, jsonify
# from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, create_access_token

# from model.Adm_Info import AdmInfo
# from model.Employee_Info import EmployeeInfo
# from server.common_server import CommonServer  # 确保从这里导入 CommonServer
# import logging

# logger = logging.getLogger(__name__)

# class RegisterResource(Resource):
#     def post(self):
#         data = request.json
#         if not data:
#             return {'message': '请求体不能为空'}, 400

#         name = data.get('name')
#         employeeId = data.get('employeeId') # 注意：前端注册时用的是 employeeId，它将被用作员工编号和工号
#         id_number = data.get('idNumber')
#         phone_number = data.get('phone')
#         password = data.get('password')
        
#         if not all([name, employeeId, id_number, phone_number, password]):
#             return {'message': '所有必填字段都不能为空'}, 400

#         # 调用 CommonServer 的注册方法
#         result = CommonServer.register_employee(
#             name=name,
#             employeeId=employeeId,
#             id_number=id_number,
#             phone_number=phone_number,
#             password=password
#         )

#         if result['status']:
#             return {'message': result['message']}, 201
#         else:
#             status_code = 409 if '已存在' in result['message'] or '已被注册' in result['message'] else 400
#             return {'message': result['message']}, status_code

# # --- 以下是你文件中其他的类，保持不变 ---
# class LoginResource(Resource):
#     def post(self):
#         data = request.json
#         username = data.get('username')
#         password = data.get('password')
#         role = data.get('role')

#         user = CommonServer.authenticate_user(username, password, role)
#         if not user:
#             return {'message': '用户名或密码错误'}, 401

#         access_token, refresh_token = CommonServer.generate_tokens(
#             user.adm_number if role == 'admin' else user.employee_number,
#             role
#         )

#         if role == 'admin':
#             user_info = AdmInfo.query.filter_by(adm_number=user.adm_number).first()
#         else:
#             user_info = EmployeeInfo.query.filter_by(employee_number=user.employee_number).first()
        
#         user_name = user_info.name if user_info else '未知用户'
        
#         return {
#             'access_token': access_token, 'refresh_token': refresh_token,
#             'permissions': [p.name for p in user.permissions] if hasattr(user, 'permissions') else [],
#             'role': role, 'user_number': user.adm_number if role == 'admin' else user.employee_number,
#             'user_name': user_name
#         }, 200

# class LogoutResource(Resource):
#     @jwt_required()
#     def post(self):
#         jti = get_jwt()['jti']
#         CommonServer.add_token_to_blocklist(jti)
#         return {'message': '成功注销'}, 200

# class ProtectResource(Resource):
#     @jwt_required()
#     def get(self):
#         current_user_id = get_jwt_identity()
#         jwt_data = get_jwt()
#         role = jwt_data['role']
#         user = CommonServer.get_user(current_user_id, role)
#         if not user:
#             return {'message': '用户不存在'}, 404
#         return {
#             'message': f'欢迎, {user.adm_user_name if role == "admin" else user.employee_user_name}!',
#             'role': role, 'user_number': current_user_id
#         }, 200

# class RefreshTokenResource(Resource):
#     @jwt_required(refresh=True)
#     def post(self):
#         current_user_id = get_jwt_identity()
#         jti = get_jwt()['jti']
#         if CommonServer.token_in_blocklist(jti):
#             return {'message': '刷新令牌已被撤销'}, 401
#         role = request.json.get('role')
#         if not role:
#             return {'message': '需要提供角色'}, 400
#         access_token, refresh_token = CommonServer.generate_tokens(current_user_id, role)
#         return jsonify({'access_token': access_token, 'refresh_token': refresh_token}), 200


from flask_restful import Resource
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, create_access_token

from model.Adm_Account import AdmAccount
from model.Employee_Info import EmployeeInfo
from server.common_server import CommonServer 
import logging

logger = logging.getLogger(__name__)

class RegisterResource(Resource):
    def post(self):
        data = request.json
        if not data:
            return {'message': '请求体不能为空'}, 400

        name = data.get('name')
        employeeId = data.get('employeeId')
        id_number = data.get('idNumber')
        phone_number = data.get('phone')
        password = data.get('password')
        
        if not all([name, employeeId, id_number, phone_number, password]):
            return {'message': '所有必填字段都不能为空'}, 400

        result = CommonServer.register_employee(
            name=name,
            employeeId=employeeId,
            id_number=id_number,
            phone_number=phone_number,
            password=password
        )

        if result['status']:
            return {'message': result['message']}, 201
        else:
            status_code = 409 if '已存在' in result['message'] or '已被注册' in result['message'] else 400
            return {'message': result['message']}, status_code

class LoginResource(Resource):
    def post(self):
        data = request.json
        username = data.get('username')
        password = data.get('password')
        role = data.get('role')

        user = CommonServer.authenticate_user(username, password, role)
        if not user:
            return {'message': '用户名或密码错误'}, 401

        access_token, refresh_token = CommonServer.generate_tokens(
            user.adm_number if role == 'admin' else user.employee_number,
            role
        )

        if role == 'admin':
            user_info = AdmAccount.query.filter_by(adm_number=user.adm_number).first()
            # 修正：AdmAccount模型中用户名为 adm_user_name
            user_name = user_info.adm_user_name if user_info else '未知用户'
        else:
            user_info = EmployeeInfo.query.filter_by(employee_number=user.employee_number).first()
            # EmployeeInfo模型中用户名为 name
            user_name = user_info.name if user_info else '未知用户'
        
        return {
            'access_token': access_token, 
            'refresh_token': refresh_token,
            'permissions': [p.name for p in user.permissions] if hasattr(user, 'permissions') else [],
            'role': role, 
            'user_number': user.adm_number if role == 'admin' else user.employee_number,
            'user_name': user_name
        }, 200

class LogoutResource(Resource):
    @jwt_required()
    def post(self):
        jti = get_jwt()['jti']
        CommonServer.add_token_to_blocklist(jti)
        return {'message': '成功注销'}, 200

class ProtectResource(Resource):
    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        jwt_data = get_jwt()
        role = jwt_data['role']
        user = CommonServer.get_user(current_user_id, role)
        if not user:
            return {'message': '用户不存在'}, 404
        return {
            'message': f'欢迎, {user.adm_user_name if role == "admin" else user.employee_user_name}!',
            'role': role, 
            'user_number': current_user_id
        }, 200

class RefreshTokenResource(Resource):
    @jwt_required(refresh=True)
    def post(self):
        current_user_id = get_jwt_identity()
        jti = get_jwt()['jti']
        if CommonServer.token_in_blocklist(jti):
            return {'message': '刷新令牌已被撤销'}, 401
        role = request.json.get('role')
        if not role:
            return {'message': '需要提供角色'}, 400
        access_token, refresh_token = CommonServer.generate_tokens(current_user_id, role)
        return jsonify({'access_token': access_token, 'refresh_token': refresh_token}), 200

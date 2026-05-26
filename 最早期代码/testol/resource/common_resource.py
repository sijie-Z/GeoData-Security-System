from flask_restful import Resource
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, create_access_token

from extension.extension import limiter
from model.Adm_Info import AdmInfo
from model.Employee_Info import EmployeeInfo
from server.common_server import CommonServer
import logging

logger = logging.getLogger(__name__)


class LoginResource(Resource):
    def post(self):
        data = request.json
        username = data.get('username')
        password = data.get('password')
        role = data.get('role')

        logger.info(f"登录尝试: 用户名={username}, 角色={role}")

        user = CommonServer.authenticate_user(username, password, role)
        if not user:
            logger.error(f"登录失败: 用户名={username}, 角色={role}")
            return {'message': '用户名或密码错误'}, 401

        access_token, refresh_token = CommonServer.generate_tokens(
            user.adm_number if role == 'admin' else user.employee_number,
            role
        )

        if role == 'admin':
            user_info = AdmInfo.query.filter_by(adm_number=user.adm_number).first()
        else:
            user_info = EmployeeInfo.query.filter_by(employee_number=user.employee_number).first()

        user_name = user_info.name if user_info else '未知用户'

        logger.info(f"登录成功: 用户名={username}, 角色={role}")
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
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200

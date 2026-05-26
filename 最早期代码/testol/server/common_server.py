from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token
from model.Adm_Account import AdmAccount
from model.Employee_Account import EmployeeAccount
from model.TokenBlacklist import TokenBlacklist
from extension.extension import db
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class CommonServer:
    @staticmethod
    def authenticate_user(username: str, password: str, role: str):
        if role == 'admin':
            user = AdmAccount.query.filter_by(adm_user_name=username).first()
            password_field = 'adm_user_password'
        elif role == 'employee':
            user = EmployeeAccount.query.filter_by(employee_user_name=username).first()
            password_field = 'employee_user_password'
        else:
            return None

        if user:
            logger.debug(f"用户 {username} 找到，验证密码中...")
            if check_password_hash(getattr(user, password_field), password):
                logger.debug(f"用户 {username} 密码验证通过")
                return user
            else:
                logger.debug(f"用户 {username} 密码验证失败")
        else:
            logger.debug(f"用户 {username} 未找到")

        return None

    @staticmethod
    def generate_tokens(user_id: str, role: str):
        access_token = create_access_token(identity=user_id, additional_claims={'role': role},
                                           expires_delta=timedelta(hours=24))
        refresh_token = create_refresh_token(identity=user_id, expires_delta=timedelta(days=30))
        return access_token, refresh_token

    @staticmethod
    def get_user(user_id: str, role: str):
        if role == 'admin':
            return AdmAccount.query.filter_by(adm_number=user_id).first()
        elif role == 'employee':
            return EmployeeAccount.query.filter_by(employee_number=user_id).first()
        return None

    @staticmethod
    def token_in_blocklist(jti: str) -> bool:
        return TokenBlacklist.query.filter_by(jti=jti).first() is not None

    @staticmethod
    def add_token_to_blocklist(jti: str) -> None:
        blacklisted_token = TokenBlacklist(jti=jti)
        db.session.add(blacklisted_token)
        db.session.commit()

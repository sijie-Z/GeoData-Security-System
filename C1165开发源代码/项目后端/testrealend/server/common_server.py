# from werkzeug.security import check_password_hash
# from flask_jwt_extended import create_access_token, create_refresh_token
# from model.Adm_Account import AdmAccount
# from model.Employee_Account import EmployeeAccount
# from model.TokenBlacklist import TokenBlacklist
# from extension.extension import db
# from datetime import timedelta
# import logging
# from werkzeug.security import generate_password_hash
# from model.Employee_Account import EmployeeAccount
# from model.Employee_Info import EmployeeInfo
# logger = logging.getLogger(__name__)


# class CommonServer:
#     @staticmethod
#     def register_employee(name: str, employee_number: str, id_number: str, phone_number: str, password: str):
#         """员工注册方法"""
#         try:
#             # 检查工号是否已存在（employee_number为主键，唯一约束）
#             if EmployeeInfo.query.filter_by(employee_number=employee_number).first():
#                 return {'status': False, 'message': '工号已存在'}
#             # 检查身份证号是否已存在
#             if EmployeeInfo.query.filter_by(id_number=id_number).first():
#                 return {'status': False, 'message': '身份证号已存在'}
#             # 检查手机号是否已存在
#             if EmployeeInfo.query.filter_by(phone_number=phone_number).first():
#                 return {'status': False, 'message': '联系电话已存在'}

#             # 创建员工信息记录
#             employee_info = EmployeeInfo(
#                 employee_number=employee_number,
#                 name=name,
#                 job_number=employee_number,  # 临时用工号作为job_number
#                 id_number=id_number,
#                 phone_number=phone_number,
#                 address='未填写',
#                 face_photo=None
#             )

#             # 创建账户记录（用户名使用工号，密码哈希处理）
#             employee_account = EmployeeAccount(
#                 employee_user_name=employee_number,  # 用户名使用工号
#                 employee_user_password=generate_password_hash(password),  # 密码哈希
#                 employee_number=employee_number
#             )

#             # 插入数据库
#             db.session.add(employee_info)
#             db.session.commit()
#             db.session.add(employee_account)
#             db.session.commit()
#             return {'status': True, 'message': '注册成功'}

#         except Exception as e:
#             db.session.rollback()  # 事务回滚
#             logger.error(f'注册失败：{str(e)}')
#             return {'status': False, 'message': '注册失败，请稍后再试'}
#     @staticmethod                       
#     def authenticate_user(username: str, password: str, role: str):
#         if role == 'admin':
#             user = AdmAccount.query.filter_by(adm_user_name=username).first()
#             password_field = 'adm_user_password'
#         elif role == 'employee':
#             user = EmployeeAccount.query.filter_by(employee_user_name=username).first()
#             password_field = 'employee_user_password'
#         else:
#             return None

#         if user:
#             logger.debug(f"用户 {username} 找到，验证密码中...")
#             if check_password_hash(getattr(user, password_field), password):
#                 logger.debug(f"用户 {username} 密码验证通过")
#                 return user
#             else:
#                 logger.debug(f"用户 {username} 密码验证失败")
#         else:
#             logger.debug(f"用户 {username} 未找到")

#         return None

#     @staticmethod
#     def generate_tokens(user_id: str, role: str):
#         access_token = create_access_token(identity=user_id, additional_claims={'role': role},
#                                            expires_delta=timedelta(hours=24))
#         refresh_token = create_refresh_token(identity=user_id, expires_delta=timedelta(days=30))
#         return access_token, refresh_token

#     @staticmethod
#     def get_user(user_id: str, role: str):
#         if role == 'admin':
#             return AdmAccount.query.filter_by(adm_number=user_id).first()
#         elif role == 'employee':
#             return EmployeeAccount.query.filter_by(employee_number=user_id).first()
#         return None

#     @staticmethod
#     def token_in_blocklist(jti: str) -> bool:
#         return TokenBlacklist.query.filter_by(jti=jti).first() is not None

#     @staticmethod
#     def add_token_to_blocklist(jti: str) -> None:
#         blacklisted_token = TokenBlacklist(jti=jti)
#         db.session.add(blacklisted_token)
#         db.session.commit()




# d:\Desktop\ESRI_test\testrealend\server\common_server.py

from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token
from model.Adm_Account import AdmAccount
from model.Employee_Account import EmployeeAccount
from model.Employee_Info import EmployeeInfo
from model.TokenBlacklist import TokenBlacklist
from extension.extension import db
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# 这个类专门处理公共的、非管理员权限的逻辑
class CommonServer:
    @staticmethod
    def register_employee(name: str, employeeId: str, id_number: str, phone_number: str, password: str):
        """
        员工注册服务。
        这个方法将前端的 employeeId 同时用作 employee_number (主键) 和 job_number。
        """
        # 预检查
        if EmployeeInfo.query.filter_by(employee_number=employeeId).first():
            return {'status': False, 'message': '该员工编号已存在'}
        if EmployeeInfo.query.filter_by(job_number=employeeId).first():
            return {'status': False, 'message': '该工号已被注册'}
        if EmployeeInfo.query.filter_by(id_number=id_number).first():
            return {'status': False, 'message': '该身份证号已存在'}
        if EmployeeInfo.query.filter_by(phone_number=phone_number).first():
            return {'status': False, 'message': '该联系电话已存在'}
            
        employee_info = EmployeeInfo(
            employee_number=employeeId,  # 使用前端传来的工号作为主键
            name=name,
            job_number=employeeId,  # 同时作为工号
            id_number=id_number,
            phone_number=phone_number,
            address='未填写'
        )

        employee_account = EmployeeAccount(
            employee_user_name=employeeId,  # 登录名也使用工号
            employee_user_password=generate_password_hash(password),
            employee_number=employeeId  # 外键关联
        )

        try:
            # 使用分两次提交的可靠方法
            db.session.add(employee_info)
            db.session.commit()

            db.session.add(employee_account)
            db.session.commit()
            return {'status': True, 'message': '注册成功'}
        except Exception as e:
            db.session.rollback()
            logger.error(f'注册失败: {str(e)}')
            # 如果出错，需要删除可能已经创建的 employee_info
            created_info = EmployeeInfo.query.filter_by(employee_number=employeeId).first()
            if created_info:
                db.session.delete(created_info)
                db.session.commit()
            return {'status': False, 'message': '注册失败，服务器内部错误'}
    
    @staticmethod                       
    def authenticate_user(username: str, password: str, role: str):
        """用户认证"""
        user = None
        if role == 'admin':
            user = AdmAccount.query.filter_by(adm_user_name=username).first()
        elif role == 'employee':
            user = EmployeeAccount.query.filter_by(employee_user_name=username).first()
        
        # 确保 user 存在，并且 user 模型有 get_password_hash 方法
        if user and hasattr(user, 'get_password_hash') and check_password_hash(user.get_password_hash(), password):
            return user
        return None

    @staticmethod
    def generate_tokens(user_id: str, role: str):
        """生成Token"""
        access_token = create_access_token(identity=user_id, additional_claims={'role': role}, expires_delta=timedelta(hours=24))
        refresh_token = create_refresh_token(identity=user_id, expires_delta=timedelta(days=30))
        return access_token, refresh_token

    @staticmethod
    def get_user(user_id: str, role: str):
        """根据ID和角色获取用户"""
        if role == 'admin':
            return AdmAccount.query.filter_by(adm_number=user_id).first()
        elif role == 'employee':
            return EmployeeAccount.query.filter_by(employee_number=user_id).first()
        return None

    @staticmethod
    def token_in_blocklist(jti: str) -> bool:
        """检查Token是否在黑名单中"""
        return TokenBlacklist.query.filter_by(jti=jti).first() is not None

    @staticmethod
    def add_token_to_blocklist(jti: str) -> None:
        """将Token加入黑名单"""
        blacklisted_token = TokenBlacklist(jti=jti)
        db.session.add(blacklisted_token)
        db.session.commit()

# 为了兼容你的 authenticate_user 逻辑，我们需要确保模型有 get_password_hash 方法
# 这是一个辅助函数，你可以在启动时调用一次，或者直接把这个方法写在你的模型文件里
def add_get_password_hash_method_to_models():
    def get_password_adm(self):
        return self.adm_user_password
    
    def get_password_emp(self):
        return self.employee_user_password

    # 动态地给类添加方法
    if not hasattr(AdmAccount, 'get_password_hash'):
        AdmAccount.get_password_hash = get_password_adm
    if not hasattr(EmployeeAccount, 'get_password_hash'):
        EmployeeAccount.get_password_hash = get_password_emp

# 在模块加载时执行这个辅助函数
add_get_password_hash_method_to_models()
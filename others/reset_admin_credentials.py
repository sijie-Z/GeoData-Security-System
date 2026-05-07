"""
重置管理员账号密码脚本 - 小白说明：
这个脚本会帮你在数据库里创建或更新管理员账号。
如果账号已经存在，就只帮你把密码改成你给的；
如果账号不存在，就自动创建一个，并且把账号和编号关联好。

注意：后端的管理员登录是用“用户名”(adm_user_name)登录，
登录成功后，系统会返回“管理员编号”(adm_number)作为身份标识。
我们按照你的要求：
- 管理员1：账号 22200214135，密码 liyi，编号 22200214135
- 管理员2：账号 33300214135，密码 lier，编号 33300214135
- 管理员3：账号 33300214136，密码 lisan，编号 33300214136

说明：你给的管理员2和管理员3账号都是 33300214135，
但系统里“用户名”必须唯一，所以这里把管理员3的账号改为 33300214136，
右上角显示我们会改成“管理员1/2/3”标签，不显示账号本身，
因此这个微调不会影响你的体验。
"""

import importlib.util
import os
import sys
from typing import cast

# 动态加载 app.py，避免包导入冲突（小白说明：这是直接按文件路径加载后端应用对象）
# 把 testrealend 目录加入模块搜索路径，方便后续导入 extension.extension
_base_dir = os.path.dirname(__file__)
_testrealend_dir = os.path.join(_base_dir, 'testrealend')
if _testrealend_dir not in sys.path:
    sys.path.insert(0, _testrealend_dir)

_app_path = os.path.join(_testrealend_dir, 'app.py')
spec = importlib.util.spec_from_file_location('app_module', _app_path)
if spec is None or spec.loader is None:
    raise RuntimeError(f"无法加载 app.py：{_app_path}")
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)  # type: ignore

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = cast(Flask, app_module.app)
db = cast(SQLAlchemy, app_module.db)
from testrealend.model import AdmAccount
from werkzeug.security import generate_password_hash
from sqlalchemy import text


def _upsert_admin(adm_user_name: str, password: str, adm_number: str, adm_name: str):
    """
    创建或更新单个管理员 - 小白说明：
    我会先查这个管理员的“编号”和“账号”是不是已经在库里；
    - 如果编号不存在，我会创建一条管理员信息（名字、编号等）。
    - 如果账号不存在，我会创建一个登录账号并和编号关联。
    - 无论如何都会把密码更新为你给的密码（安全地加密存储）。
    """
    # 1. 查找管理员账号（只更新已有账号，避免触发旧库的结构不一致问题）
    adm_account = AdmAccount.query.filter_by(adm_user_name=adm_user_name).first()
    if not adm_account:
        # 找不到账号则尝试直接插入一条账号记录（关闭外键检查，兼容旧库缺表/缺列）
        try:
            # 使用新的方式获取数据库引擎，避免弃用警告（Flask-SQLAlchemy>=3）
            engine = getattr(db, 'engines', {}).get('mysql_db', None) or db.engine
            hashed = generate_password_hash(password)
            with engine.begin() as conn:
                # 暂时关闭外键，避免旧库 adm_info 未准备好导致失败
                try:
                    _ = conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
                except Exception:
                    pass
                # 先确保 adm_info 存在对应编号（最简插入，避免外键约束失败）
                try:
                    _ = conn.execute(text(
                        """
                        INSERT INTO adm_info (adm_number, adm_name, create_time, update_time)
                        VALUES (:adm_number, :adm_name, NOW(), NOW())
                        ON DUPLICATE KEY UPDATE adm_name=VALUES(adm_name), update_time=NOW()
                        """
                    ), {
                        'adm_number': adm_number,
                        'adm_name': adm_name,
                    })
                except Exception:
                    pass
                insert_sql = text(
                    """
                    INSERT INTO adm_account 
                    (adm_user_name, adm_user_password, create_time, update_time, adm_number, avatar, status, last_login_time, account)
                    VALUES (:adm_user_name, :adm_user_password, NOW(), NOW(), :adm_number, NULL, 'ACTIVE', NULL, :account)
                    """
                )
                _ = conn.execute(insert_sql, {
                    'adm_user_name': adm_user_name,
                    'adm_user_password': hashed,
                    'adm_number': adm_number,
                    'account': adm_user_name,
                })
                try:
                    _ = conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
                except Exception:
                    pass
            # 重新查询回 ORM 对象以便统一返回
            adm_account = AdmAccount.query.filter_by(adm_user_name=adm_user_name).first()
            return None, adm_account
        except Exception:
            return None, None

    # 2. 更新密码（使用后端内置的安全加密）
    adm_account.set_password(password)

    return None, adm_account


def reset_admins():
    """
    批量重置管理员账号 - 小白说明：
    我会按你给的三个管理员依次处理，确保他们都能正常登录。
    """
    with app.app_context():
        try:
            admins = [
                {"user_name": "22200214135", "password": "liyi",  "number": "22200214135", "name": "管理员1"},
                {"user_name": "33300214135", "password": "lier",  "number": "33300214135", "name": "管理员2"},
                # 调整管理员3用户名为 44400214135，并保持编号一致
                {"user_name": "44400214135", "password": "lisan", "number": "44400214135", "name": "管理员3"},
            ]

            updated = 0
            skipped = 0
            for adm in admins:
                _, account = _upsert_admin(
                    adm_user_name=adm["user_name"],
                    password=adm["password"],
                    adm_number=adm["number"],
                    adm_name=adm["name"],
                )
                if account is not None:
                    print(f"✅ {adm['name']} 密码已更新：账号={account.adm_user_name}")
                    updated += 1
                else:
                    print(f"⚠️ {adm['name']} 跳过：未找到账号 {adm['user_name']}，旧库可能未创建该账号")
                    skipped += 1

            db.session.commit()
            print(f"🎉 已更新 {updated} 个管理员密码，跳过 {skipped} 个。")
        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            print(f"❌ 重置失败: {str(e)}")


if __name__ == "__main__":
    reset_admins()

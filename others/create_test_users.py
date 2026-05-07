#!/usr/bin/env python3
"""
创建测试用户账户
用于验证登录功能
小白讲解：这个脚本会在数据库里创建几个测试账户，让我们可以测试登录功能
"""

import sys
from pathlib import Path
from datetime import datetime

# 将项目根目录加入 Python 路径，确保可导入 testrealend 包
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from werkzeug.security import generate_password_hash
from testrealend.model.models import db, EmployeeAccount, AdmAccount
from testrealend.app import app


def create_test_users():
    """
    小白讲解：创建测试用户，包括普通员工和管理员
    """
    print("开始创建测试用户...")

    try:
        # 创建普通员工账户
        employee = EmployeeAccount(
            employee_id='EMP001',
            name='张三',
            email='zhangsan@test.com',
            password=generate_password_hash('123456'),
            phone='13800138000',
            department='遥感数据部',
            position='数据分析师',
            role='employee',
            status='active',
            avatar=None,
            created_at=datetime.now()
        )

        # 创建管理员账户
        admin = AdmAccount(
            adm_id='ADM001',
            name='李四管理员',
            email='admin@test.com',
            password=generate_password_hash('admin123'),
            phone='13900139000',
            department='系统管理部',
            position='系统管理员',
            role='admin',
            status='active',
            avatar=None,
            created_at=datetime.now()
        )

        # 保存到数据库
        db.session.add(employee)
        db.session.add(admin)
        db.session.commit()

        print("✅ 测试用户创建成功！")
        print("普通员工账户：")
        print("- 用户名：zhangsan@test.com")
        print("- 密码：123456")
        print("- 员工ID：EMP001")
        print()
        print("管理员账户：")
        print("- 用户名：admin@test.com")
        print("- 密码：admin123")
        print("- 管理员ID：ADM001")
        print()
        print("现在可以用这些账户测试登录功能了！")

    except Exception as e:
        print(f"❌ 创建用户失败：{e}")
        db.session.rollback()
        return False

    return True


if __name__ == '__main__':
    with app.app_context():
        create_test_users()

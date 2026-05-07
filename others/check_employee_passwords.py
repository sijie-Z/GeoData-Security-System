#!/usr/bin/env python3
"""
检查员工账号密码 - 小白说明：这个脚本用来查看员工账号的密码哈希
"""

import sys
sys.path.append('testrealend')

from testrealend.app import app  # 导入Flask应用
from testrealend.model.models import EmployeeAccount

def check_employee_passwords():
    """检查员工账号密码"""
    with app.app_context():
        # 查询所有员工账号
        all_accounts = EmployeeAccount.query.all()
        print(f"=== 员工账号密码信息 ===")
        print(f"总账号数：{len(all_accounts)}")
        
        for account in all_accounts:
            print(f"\n用户名：{account.employee_user_name}")
            print(f"员工编号：{account.employee_number}")
            print(f"密码哈希：{account.employee_user_password}")
            
            # 尝试检查密码（测试用）
            test_passwords = ['123456', 'test123456', 'password', '12345678']
            for pwd in test_passwords:
                if account.check_password(pwd):
                    print(f"✅ 密码匹配：{pwd}")
                    break
            else:
                print("❌ 常用密码不匹配")

if __name__ == '__main__':
    check_employee_passwords()
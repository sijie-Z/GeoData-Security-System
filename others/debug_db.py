#!/usr/bin/env python3
"""
数据库查询调试脚本 - 小白说明：这个脚本用来检查数据库中的员工信息
"""

import sys
sys.path.append('testrealend')

from testrealend.app import app  # 导入Flask应用
from testrealend.model.models import EmployeeAccount, EmployeeInfo

def check_employee_data(username):
    """检查员工数据完整性"""
    print(f"=== 检查员工数据：{username} ===")
    
    with app.app_context():
        # 查询员工账号
        emp_account = EmployeeAccount.query.filter_by(employee_user_name=username).first()
        print(f"员工账号：{emp_account}")
        
        if emp_account:
            print(f"员工编号：{emp_account.employee_number}")
            print(f"员工用户名：{emp_account.employee_user_name}")
            
            # 查询员工信息
            emp_info = EmployeeInfo.query.filter_by(employee_number=emp_account.employee_number).first()
            print(f"员工信息：{emp_info}")
            
            if emp_info:
                print(f"员工姓名：{emp_info.name}")
                print(f"员工电话：{emp_info.phone_number}")
                print(f"员工地址：{emp_info.address}")
                print("✅ 员工数据完整")
            else:
                print("❌ 员工信息不存在")
        else:
            print("❌ 员工账号不存在")
        
        print("\n=== 所有员工账号 ===")
        all_accounts = EmployeeAccount.query.all()
        for account in all_accounts:
            print(f"用户名：{account.employee_user_name}, 编号：{account.employee_number}")
        
        print("\n=== 所有员工信息 ===")
        all_infos = EmployeeInfo.query.all()
        print(f"员工信息总数: {len(all_infos)}")
        if all_infos:
            for info in all_infos:
                if info:  # 检查是否为None
                    print(f"编号：{info.employee_number}, 姓名：{info.name}, 电话：{info.phone_number}")
        else:
            print("没有任何员工信息记录")
            
        # 专门查询test2025_new的员工信息
        print(f"\n=== 专门查询test2025_new ===")
        test_info = EmployeeInfo.query.filter_by(employee_number='test2025_new').first()
        print(f"test2025_new员工信息: {test_info}")
        if test_info:
            print(f"编号：{test_info.employee_number}, 姓名：{test_info.name}, 电话：{test_info.phone_number}")

if __name__ == "__main__":
    check_employee_data("test2026_new")  # 检查新注册的员工
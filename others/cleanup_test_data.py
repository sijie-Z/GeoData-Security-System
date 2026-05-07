#!/usr/bin/env python3
"""
清理测试数据脚本
小白说明：这个脚本用来清理测试时产生的重复数据
"""

import sys
import os

# 让脚本可从项目任意位置启动
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from testrealend.app import get_app
from testrealend.extension.extension import db
from testrealend.model import EmployeeAccount, EmployeeInfo

app = get_app()

def cleanup_test_data():
    """清理测试数据"""
    with app.app_context():
        try:
            # 清理有问题的员工账号和信息
            test_employees = ['test123', 'testnew', 'debugemp', 'test2024_new']
            
            for emp_id in test_employees:
                # 删除员工账号
                emp_account = EmployeeAccount.query.filter_by(employee_user_name=emp_id).first()
                if emp_account:
                    print(f"删除员工账号: {emp_id}")
                    db.session.delete(emp_account)
                
                # 删除员工信息
                emp_info = EmployeeInfo.query.filter_by(employee_number=emp_id).first()
                if emp_info:
                    print(f"删除员工信息: {emp_id}")
                    db.session.delete(emp_info)
            
            # 清理重复的身份证号
            duplicate_id_numbers = ['123456789012345670', '123456789012345678']
            for id_number in duplicate_id_numbers:
                emp_info = EmployeeInfo.query.filter_by(id_number=id_number).first()
                if emp_info:
                    print(f"删除重复身份证号的员工信息: {id_number}")
                    db.session.delete(emp_info)
            
            db.session.commit()
            print("测试数据清理完成！")
            
        except Exception as e:
            db.session.rollback()
            print(f"清理数据时出错: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    cleanup_test_data()
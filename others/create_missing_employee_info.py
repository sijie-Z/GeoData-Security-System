#!/usr/bin/env python3
"""
手动创建员工信息 - 小白说明：这个脚本用来手动创建缺失的员工信息记录
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(project_root, 'testrealend'))

# 导入Flask应用和模型
from testrealend.app import app
from testrealend.extension.extension import db
from testrealend.model.models import EmployeeAccount, EmployeeInfo

def create_missing_employee_info():
    """为没有员工信息的账号创建信息记录"""
    with app.app_context():
        # 获取所有员工账号
        all_accounts = EmployeeAccount.query.all()
        print(f"=== 开始检查员工信息完整性 ===")
        
        created_count = 0
        
        for account in all_accounts:
            print(f"\n检查员工账号：{account.employee_user_name} ({account.employee_number})")
            
            # 检查对应的员工信息是否存在
            emp_info = EmployeeInfo.query.filter_by(employee_number=account.employee_number).first()
            
            if emp_info:
                print(f"✅ 员工信息已存在 - 姓名：{emp_info.name}")
            else:
                print(f"❌ 员工信息不存在，正在创建...")
                
                try:
                    # 创建员工信息记录
                    new_info = EmployeeInfo(
                        employee_number=account.employee_number,
                        name='未设置',
                        job_number=account.employee_number,
                        id_number='未设置',
                        phone_number='未设置',
                        address='未设置'
                    )
                    
                    db.session.add(new_info)
                    db.session.commit()
                    
                    created_count += 1
                    print(f"✅ 成功创建员工信息记录")
                    
                except Exception as e:
                    db.session.rollback()
                    print(f"❌ 创建失败：{e}")
        
        print(f"\n=== 完成 ===")
        print(f"总共检查了 {len(all_accounts)} 个员工账号")
        print(f"创建了 {created_count} 个员工信息记录")

if __name__ == '__main__':
    create_missing_employee_info()
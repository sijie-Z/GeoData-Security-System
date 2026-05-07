#!/usr/bin/env python3
"""
直接SQL创建员工信息 - 小白说明：这个脚本用SQL直接创建缺失的员工信息记录
"""

import sys
sys.path.append('testrealend')

from testrealend.app import app  # 导入Flask应用
from testrealend.extension.extension import db

def create_missing_employee_info_sql():
    """用SQL直接为缺失员工信息的账号创建记录"""
    with app.app_context():
        print("=== 开始用SQL创建缺失的员工信息 ===")
        
        # 查找没有对应员工信息的员工账号
        sql = """
        SELECT ea.employee_number, ea.employee_user_name 
        FROM employee_account ea 
        LEFT JOIN employee_info ei ON ea.employee_number = ei.employee_number 
        WHERE ei.employee_number IS NULL
        """
        
        result = db.session.execute(db.text(sql))
        missing_accounts = result.fetchall()
        
        print(f"发现 {len(missing_accounts)} 个缺失员工信息的账号")
        
        created_count = 0
        for account in missing_accounts:
            employee_number = account[0]
            employee_user_name = account[1]
            
            print(f"\n为账号 {employee_user_name} ({employee_number}) 创建员工信息...")
            
            try:
                # 使用SQL直接插入
                insert_sql = """
                INSERT INTO employee_info (employee_number, name, job_number, id_number, phone_number, address, create_time, update_time) 
                VALUES (:employee_number, :name, :job_number, :id_number, :phone_number, :address, NOW(), NOW())
                """
                
                db.session.execute(db.text(insert_sql), {
                    'employee_number': employee_number,
                    'name': '未设置',
                    'job_number': employee_number,
                    'id_number': '未设置',
                    'phone_number': '未设置',
                    'address': '未设置'
                })
                
                db.session.commit()
                created_count += 1
                print(f"✅ 成功创建员工信息记录")
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ 创建失败：{e}")
        
        print(f"\n=== 完成 ===")
        print(f"成功创建了 {created_count} 个员工信息记录")

if __name__ == '__main__':
    create_missing_employee_info_sql()
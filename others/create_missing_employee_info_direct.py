#!/usr/bin/env python3
"""
直接操作数据库创建员工信息 - 小白说明：这个脚本直接连接数据库创建缺失的员工信息
"""

import pymysql

def create_missing_employee_info_direct():
    """直接连接数据库创建缺失的员工信息"""
    
    # 数据库连接配置
    connection = pymysql.connect(
        host='127.0.0.1',
        user='root',
        password='root',
        database='esri_test',
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            print("=== 开始检查员工信息完整性 ===")
            
            # 查找没有对应员工信息的员工账号
            sql = """
            SELECT ea.employee_number, ea.employee_user_name 
            FROM employee_account ea 
            LEFT JOIN employee_info ei ON ea.employee_number = ei.employee_number 
            WHERE ei.employee_number IS NULL
            """
            
            cursor.execute(sql)
            missing_accounts = cursor.fetchall()
            
            print(f"发现 {len(missing_accounts)} 个缺失员工信息的账号")
            
            created_count = 0
            for account in missing_accounts:
                employee_number = account[0]
                employee_user_name = account[1]
                
                print(f"\n为账号 {employee_user_name} ({employee_number}) 创建员工信息...")
                
                try:
                    # 插入员工信息
                    insert_sql = """
                    INSERT INTO employee_info (employee_number, name, job_number, id_number, phone_number, address, create_time, update_time) 
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """
                    
                    cursor.execute(insert_sql, (
                        employee_number,
                        '未设置',
                        employee_number,
                        '未设置',
                        '未设置',
                        '未设置'
                    ))
                    
                    connection.commit()
                    created_count += 1
                    print(f"✅ 成功创建员工信息记录")
                    
                except Exception as e:
                    connection.rollback()
                    print(f"❌ 创建失败：{e}")
            
            print(f"\n=== 完成 ===")
            print(f"成功创建了 {created_count} 个员工信息记录")
            
            # 验证结果
            cursor.execute("SELECT COUNT(*) FROM employee_info")
            total_row = cursor.fetchone()
            total_count = total_row[0] if total_row is not None else 0
            print(f"现在员工信息表共有 {total_count} 条记录")
            
    finally:
        connection.close()

if __name__ == '__main__':
    create_missing_employee_info_direct()
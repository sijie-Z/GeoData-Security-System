#!/usr/bin/env python3
"""
检查数据库中的员工数据
小白说明：这个脚本用来检查员工账号和信息的对应关系
"""

import pymysql

def check_employee_data():
    """检查员工数据"""
    connection = None
    try:
        # 连接数据库
        connection = pymysql.connect(
            host='127.0.0.1',
            user='root',
            password='root',
            database='esri_test',
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # 检查test_new_001的员工账号
            print("=== 检查员工账号 ===")
            cursor.execute("SELECT * FROM employee_account WHERE employee_user_name = 'test_new_001'")
            account_result = cursor.fetchone()
            if account_result:
                print(f"找到员工账号: {account_result}")
                employee_number = account_result[2]  # employee_number字段
                print(f"员工编号: {employee_number}")
                
                # 检查对应的员工信息
                print("=== 检查员工信息 ===")
                cursor.execute("SELECT * FROM employee_info WHERE employee_number = %s", (employee_number,))
                info_result = cursor.fetchone()
                if info_result:
                    print(f"找到员工信息: {info_result}")
                    print(f"员工姓名: {info_result[2]}")
                    print(f"员工编号: {info_result[1]}")
                else:
                    print("❌ 未找到对应的员工信息")
            else:
                print("❌ 未找到员工账号")
            
            # 检查所有员工数据
            print("\n=== 检查所有员工数据 ===")
            cursor.execute("SELECT COUNT(*) FROM employee_account")
            row = cursor.fetchone()
            account_count = row[0] if row else 0
            print(f"员工账号总数: {account_count}")
            
            cursor.execute("SELECT COUNT(*) FROM employee_info")
            row = cursor.fetchone()
            info_count = row[0] if row else 0
            print(f"员工信息总数: {info_count}")
            
            # 检查是否有孤立的员工信息（没有对应账号）
            cursor.execute("""
                SELECT ei.employee_number, ei.name 
                FROM employee_info ei 
                LEFT JOIN employee_account ea ON ei.employee_number = ea.employee_number 
                WHERE ea.employee_number IS NULL
            """)
            orphaned_info = cursor.fetchall()
            if orphaned_info:
                print(f"⚠️  发现 {len(orphaned_info)} 条孤立的员工信息:")
                for info in orphaned_info:
                    print(f"  - 员工编号: {info[0]}, 姓名: {info[1]}")
            else:
                print("✅ 没有孤立的员工信息")
            
            # 检查是否有孤立的员工账号（没有对应信息）
            cursor.execute("""
                SELECT ea.employee_user_name, ea.employee_number 
                FROM employee_account ea 
                LEFT JOIN employee_info ei ON ea.employee_number = ei.employee_number 
                WHERE ei.employee_number IS NULL
            """)
            orphaned_accounts = cursor.fetchall()
            if orphaned_accounts:
                print(f"⚠️  发现 {len(orphaned_accounts)} 个孤立的员工账号:")
                for account in orphaned_accounts:
                    print(f"  - 用户名: {account[0]}, 员工编号: {account[1]}")
            else:
                print("✅ 没有孤立的员工账号")
            
    except Exception as e:
        print(f"检查数据时出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if connection is not None:
            connection.close()

if __name__ == "__main__":
    print("=== 检查员工数据完整性 ===")
    check_employee_data()

#!/usr/bin/env python3
"""
详细检查员工数据
小白说明：检查emp_test_2024的详细数据
"""

import pymysql

def check_employee_detail():
    """详细检查员工数据"""
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
            # 检查员工账号
            print("=== 员工账号详情 ===")
            cursor.execute("SELECT id, employee_user_name, employee_number FROM employee_account WHERE employee_user_name = 'emp_test_2024'")
            account = cursor.fetchone()
            if account:
                print(f"账号ID: {account[0]}")
                print(f"用户名: {account[1]}")
                print(f"员工编号: {account[2]}")
                employee_number = account[2]
                
                # 检查员工信息
                print(f"\n=== 员工信息详情 ===")
                cursor.execute("SELECT * FROM employee_info WHERE employee_number = %s", (employee_number,))
                info = cursor.fetchone()
                if info:
                    print(f"信息ID: {info[0]}")
                    print(f"员工编号: {info[1]}")
                    print(f"姓名: {info[2]}")
                    print(f"工号: {info[3]}")
                    print(f"身份证: {info[4]}")
                    print(f"电话: {info[5]}")
                    print(f"地址: {info[6]}")
                    print("✅ 找到对应的员工信息！")
                else:
                    print(f"❌ 未找到员工编号为 '{employee_number}' 的员工信息")
                    
                    # 检查所有员工信息
                    print(f"\n=== 所有员工信息 ===")
                    cursor.execute("SELECT employee_number, name FROM employee_info LIMIT 10")
                    all_info = cursor.fetchall()
                    for info in all_info:
                        print(f"员工编号: {info[0]}, 姓名: {info[1]}")
            else:
                print("❌ 未找到员工账号")
                
    except Exception as e:
        print(f"检查数据时出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if connection is not None:
            connection.close()

if __name__ == "__main__":
    print("=== 详细检查员工数据 ===")
    check_employee_detail()

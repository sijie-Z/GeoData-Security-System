#!/usr/bin/env python3
"""
检查新员工数据
小白说明：检查emp_test_2024的数据
"""

import pymysql

def check_new_employee():
    """检查新员工数据"""
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
            # 检查新员工账号
            print("=== 检查新员工账号 ===")
            cursor.execute("SELECT * FROM employee_account WHERE employee_user_name = 'emp_test_2024'")
            account_result = cursor.fetchone()
            if account_result:
                print(f"找到员工账号: ID={account_result[0]}, 用户名={account_result[1]}, 员工编号={account_result[5]}")
                employee_number = account_result[5]
                
                # 检查对应的员工信息
                print("=== 检查新员工信息 ===")
                cursor.execute("SELECT * FROM employee_info WHERE employee_number = %s", (employee_number,))
                info_result = cursor.fetchone()
                if info_result:
                    print(f"找到员工信息: ID={info_result[0]}, 员工编号={info_result[1]}, 姓名={info_result[2]}")
                    print(f"工号: {info_result[3]}, 身份证: {info_result[4]}, 电话: {info_result[5]}")
                    print("✅ 员工数据完整！")
                else:
                    print("❌ 未找到对应的员工信息")
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
    print("=== 检查新员工数据 ===")
    check_new_employee()

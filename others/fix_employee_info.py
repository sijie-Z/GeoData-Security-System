#!/usr/bin/env python3
"""
修复员工信息数据
小白说明：修复字段对应关系
"""

import pymysql

def fix_employee_info():
    """修复员工信息数据"""
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
            # 查看当前的emp_test_2024数据
            print("=== 修复前的数据 ===")
            cursor.execute("SELECT * FROM employee_info WHERE employee_number = 'emp_test_2024'")
            old_data = cursor.fetchone()
            if old_data:
                print(f"当前数据: {old_data}")
                
                # 根据表结构重新插入正确数据
                # 表结构: id, name, job_number, id_number, phone_number, address, create_time, update_time, face_photo, employee_number
                correct_data = {
                    'name': '李四',
                    'job_number': 'emp_test_2024',
                    'id_number': '110105199003079999',
                    'phone_number': '13912345678',
                    'address': '未填写',
                    'employee_number': 'emp_test_2024'
                }
                
                # 先删除错误数据
                cursor.execute("DELETE FROM employee_info WHERE employee_number = 'emp_test_2024'")
                
                # 插入正确数据
                insert_sql = """
                    INSERT INTO employee_info 
                    (name, job_number, id_number, phone_number, address, employee_number, create_time, update_time) 
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                """
                cursor.execute(insert_sql, (
                    correct_data['name'],
                    correct_data['job_number'],
                    correct_data['id_number'],
                    correct_data['phone_number'],
                    correct_data['address'],
                    correct_data['employee_number']
                ))
                
                connection.commit()
                print("✅ 数据修复完成！")
                
                # 验证修复结果
                cursor.execute("SELECT * FROM employee_info WHERE employee_number = 'emp_test_2024'")
                new_data = cursor.fetchone()
                if new_data:
                    print(f"修复后数据: {new_data}")
            else:
                print("❌ 未找到需要修复的数据")
                
    except Exception as e:
        print(f"修复数据时出错: {e}")
        if 'connection' in locals():
            connection.rollback()
        import traceback
        traceback.print_exc()
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    print("=== 修复员工信息数据 ===")
    fix_employee_info()
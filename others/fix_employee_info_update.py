#!/usr/bin/env python3
"""
修复员工信息数据 - 使用UPDATE
小白说明：用UPDATE修复字段对应关系
"""

import pymysql

def fix_employee_info_with_update():
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
                
                # 根据表结构更新正确数据
                # 表结构: id, name, job_number, id_number, phone_number, address, create_time, update_time, face_photo, employee_number
                update_sql = """
                    UPDATE employee_info 
                    SET 
                        name = '李四',
                        job_number = 'emp_test_2024',
                        id_number = '110105199003079999',
                        phone_number = '13912345678',
                        address = '未填写'
                    WHERE employee_number = 'emp_test_2024'
                """
                cursor.execute(update_sql)
                
                connection.commit()
                print("✅ 数据修复完成！")
                
                # 验证修复结果
                cursor.execute("SELECT * FROM employee_info WHERE employee_number = 'emp_test_2024'")
                new_data = cursor.fetchone()
                if new_data:
                    print(f"修复后数据: {new_data}")
                    
                    # 检查字段对应关系
                    print(f"\n=== 字段对应检查 ===")
                    print(f"员工编号 (employee_number): {new_data[9]}")  # 第10个字段
                    print(f"姓名 (name): {new_data[1]}")  # 第2个字段
                    print(f"工号 (job_number): {new_data[2]}")  # 第3个字段
                    print(f"身份证 (id_number): {new_data[3]}")  # 第4个字段
                    print(f"电话 (phone_number): {new_data[4]}")  # 第5个字段
                    print(f"地址 (address): {new_data[5]}")  # 第6个字段
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
    fix_employee_info_with_update()
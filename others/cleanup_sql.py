#!/usr/bin/env python3
"""
清理测试数据脚本 - 直接SQL版本
小白说明：这个脚本用SQL语句直接清理测试数据
"""

import pymysql

def cleanup_with_sql():
    """使用SQL直接清理数据"""
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
            # 要清理的员工编号
            test_employees = ['test123', 'testnew', 'debugemp', 'test2024_new']
            
            for emp_id in test_employees:
                # 先删除员工账号（外键依赖）
                delete_account_sql = "DELETE FROM employee_account WHERE employee_user_name = %s"
                cursor.execute(delete_account_sql, (emp_id,))
                print(f"删除员工账号: {emp_id}, 影响行数: {cursor.rowcount}")
                
                # 再删除员工信息
                delete_info_sql = "DELETE FROM employee_info WHERE employee_number = %s"
                cursor.execute(delete_info_sql, (emp_id,))
                print(f"删除员工信息: {emp_id}, 影响行数: {cursor.rowcount}")
            
            # 清理重复的身份证号
            duplicate_id_numbers = ['123456789012345670', '123456789012345678']
            for id_number in duplicate_id_numbers:
                delete_sql = "DELETE FROM employee_info WHERE id_number = %s"
                cursor.execute(delete_sql, (id_number,))
                print(f"删除重复身份证号的员工信息: {id_number}, 影响行数: {cursor.rowcount}")
            
            # 提交事务
            connection.commit()
            print("测试数据清理完成！")
            
    except Exception as e:
        print(f"清理数据时出错: {e}")
        if 'connection' in locals():
            connection.rollback()
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    cleanup_with_sql()
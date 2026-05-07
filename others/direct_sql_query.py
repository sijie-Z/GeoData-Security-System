#!/usr/bin/env python3
"""
直接SQL查询测试
小白说明：用SQL直接查询员工信息
"""

import pymysql

def direct_sql_query():
    """直接SQL查询"""
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
            # 直接查询员工信息
            print("=== 直接SQL查询 ===")
            sql = "SELECT * FROM employee_info WHERE employee_number = 'emp_test_2024'"
            cursor.execute(sql)
            result = cursor.fetchone()
            
            if result:
                print(f"✅ SQL查询成功！结果: {result}")
                print(f"员工编号: {result[9]}")  # 第10个字段是employee_number
                print(f"姓名: {result[1]}")     # 第2个字段是name
            else:
                print("❌ SQL查询无结果")
                
            # 检查是否有空格或其他字符
            print(f"\n=== 检查员工编号格式 ===")
            cursor.execute("SELECT employee_number, LENGTH(employee_number), HEX(employee_number) FROM employee_info WHERE employee_number LIKE '%emp_test_2024%'")
            format_check = cursor.fetchone()
            if format_check:
                print(f"员工编号: '{format_check[0]}'")
                print(f"长度: {format_check[1]}")
                print(f"十六进制: {format_check[2]}")
            else:
                print("❌ 未找到类似的员工编号")
                
    except Exception as e:
        print(f"查询失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    print("=== 直接SQL查询测试 ===")
    direct_sql_query()
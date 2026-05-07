#!/usr/bin/env python3
"""
检查数据库表结构
小白说明：检查employee_info表的字段顺序
"""

import pymysql

def check_table_structure():
    """检查表结构"""
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
            # 检查employee_info表结构
            print("=== employee_info表结构 ===")
            cursor.execute("DESCRIBE employee_info")
            columns = cursor.fetchall()
            for i, col in enumerate(columns):
                print(f"{i+1}. {col[0]} - {col[1]} - {col[2]} - {col[3]} - {col[4]} - {col[5]}")
            
            print(f"\n=== employee_account表结构 ===")
            cursor.execute("DESCRIBE employee_account")
            columns = cursor.fetchall()
            for i, col in enumerate(columns):
                print(f"{i+1}. {col[0]} - {col[1]} - {col[2]} - {col[3]} - {col[4]} - {col[5]}")
                
    except Exception as e:
        print(f"检查表结构时出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if connection is not None:
            connection.close()

if __name__ == "__main__":
    print("=== 检查数据库表结构 ===")
    check_table_structure()

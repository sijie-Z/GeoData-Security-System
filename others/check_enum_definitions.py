#!/usr/bin/env python3
"""
检查数据库中的枚举类型定义
小白讲解：查看数据库中实际的枚举类型定义
"""

import mysql.connector  # pyright: ignore[reportMissingImports]

def check_enum_definitions():
    """
    小白讲解：检查数据库中的枚举类型定义
    """
    try:
        # 连接数据库
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root',
            database='esri_test',
            port=3306
        )
        
        cursor = conn.cursor()
        
        # 查看employee_account表的status字段定义
        cursor.execute("SHOW CREATE TABLE employee_account")
        result = cursor.fetchone()
        print("employee_account表结构：")
        print(result[1])
        print()
        
        # 查看adm_account表的status字段定义
        cursor.execute("SHOW CREATE TABLE adm_account")
        result = cursor.fetchone()
        print("adm_account表结构：")
        print(result[1])
        print()
        
        # 查看当前数据
        cursor.execute("SELECT DISTINCT status FROM employee_account")
        employee_statuses = cursor.fetchall()
        print("employee_account表中的状态值：")
        for status in employee_statuses:
            print(f"  - {status[0]}")
        print()
        
        cursor.execute("SELECT DISTINCT status FROM adm_account")
        admin_statuses = cursor.fetchall()
        print("adm_account表中的状态值：")
        for status in admin_statuses:
            print(f"  - {status[0]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"检查枚举定义失败：{e}")
        return False

if __name__ == '__main__':
    check_enum_definitions()
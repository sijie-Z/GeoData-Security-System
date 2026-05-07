#!/usr/bin/env python3
"""
检查数据库表结构
小白讲解：这个脚本会查看数据库里实际的表结构，看看缺什么字段
"""

import mysql.connector  # pyright: ignore[reportMissingImports]

def check_database_structure():
    """
    小白讲解：检查数据库表结构，看看有哪些字段
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
        
        # 查看所有表
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print("数据库中的表：")
        for table in tables:
            table_name = table[0]
            print(f"\n=== {table_name} ===")
            
            # 查看表结构
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            
            print("字段信息：")
            for column in columns:
                field_name = column[0]
                field_type = column[1]
                _null_allowed = column[2]
                key = column[3]
                _default = column[4]
                extra = column[5]
                
                print(f"  {field_name}: {field_type} {key} {extra}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"检查数据库失败：{e}")
        return False

if __name__ == '__main__':
    check_database_structure()
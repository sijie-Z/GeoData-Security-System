#!/usr/bin/env python3
"""
检查员工信息表的完整字段结构
"""

import pymysql

def check_employee_info_fields():
    """检查员工信息表的所有字段"""
    print("=== 员工信息表字段详情 ===")
    
    connection = None
    try:
        connection = pymysql.connect(
            host='127.0.0.1',
            user='root',
            password='root',
            database='esri_test'
        )
        
        with connection.cursor() as cursor:
            # 获取员工信息表的完整字段信息
            cursor.execute("""
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT,
                    COLUMN_COMMENT,
                    COLUMN_KEY,
                    EXTRA
                FROM 
                    INFORMATION_SCHEMA.COLUMNS 
                WHERE 
                    TABLE_SCHEMA = 'esri_test' 
                    AND TABLE_NAME = 'employee_info'
                ORDER BY 
                    ORDINAL_POSITION
            """)
            
            columns = cursor.fetchall()
            print("员工信息表字段：")
            for col in columns:
                nullable = "可空" if col[2] == 'YES' else "非空"
                key_type = ""
                if col[5] == 'PRI':
                    key_type = "【主键】"
                elif col[5] == 'UNI':
                    key_type = "【唯一】"
                elif col[5] == 'MUL':
                    key_type = "【外键】"
                
                extra = f" ({col[6]})" if col[6] else ""
                
                print(f"  {col[0]}: {col[1]} {nullable} {key_type}{extra}")
                print(f"    注释: {col[4]}")
                if col[3] is not None:
                    print(f"    默认值: {col[3]}")
                print()
                
    except Exception as e:
        print(f"数据库查询错误：{str(e)}")
    finally:
        if connection is not None:
            connection.close()

if __name__ == "__main__":
    check_employee_info_fields()

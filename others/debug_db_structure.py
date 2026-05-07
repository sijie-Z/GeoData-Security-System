#!/usr/bin/env python3
"""
数据库结构调试脚本 - 小白专用
用于检查员工账号和员工信息表的字段映射
"""

import pymysql

def check_database_structure():
    """检查数据库表结构"""
    print("=== 数据库结构检查 ===")
    
    try:
        connection = pymysql.connect(
            host='127.0.0.1',
            user='root',
            password='root',
            database='esri_test'
        )
        
        with connection.cursor() as cursor:
            # 检查员工账号表结构
            print("--- 员工账号表结构 ---")
            cursor.execute("DESCRIBE employee_account")
            account_structure = cursor.fetchall()
            for column in account_structure:
                print(f"  {column[0]}: {column[1]} {'NULL' if column[2] == 'YES' else 'NOT NULL'} {'UNIQUE' if column[3] == 'UNI' else ''}")
            
            # 检查员工信息表结构
            print("\n--- 员工信息表结构 ---")
            cursor.execute("DESCRIBE employee_info")
            info_structure = cursor.fetchall()
            for column in info_structure:
                print(f"  {column[0]}: {column[1]} {'NULL' if column[2] == 'YES' else 'NOT NULL'} {'UNIQUE' if column[3] == 'UNI' else ''}")
            
            # 检查外键约束
            print("\n--- 外键约束 ---")
            cursor.execute("""
                SELECT 
                    TABLE_NAME, 
                    COLUMN_NAME, 
                    CONSTRAINT_NAME, 
                    REFERENCED_TABLE_NAME, 
                    REFERENCED_COLUMN_NAME 
                FROM 
                    INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                WHERE 
                    REFERENCED_TABLE_NAME IS NOT NULL 
                    AND TABLE_SCHEMA = 'esri_test'
                    AND TABLE_NAME IN ('employee_account', 'employee_info')
            """)
            foreign_keys = cursor.fetchall()
            if foreign_keys:
                for fk in foreign_keys:
                    print(f"  {fk[0]}.{fk[1]} -> {fk[3]}.{fk[4]} ({fk[2]})")
            else:
                print("  没有外键约束")
                
            # 检查索引
            print("\n--- 索引信息 ---")
            cursor.execute("""
                SELECT 
                    TABLE_NAME, 
                    INDEX_NAME, 
                    COLUMN_NAME, 
                    NON_UNIQUE 
                FROM 
                    INFORMATION_SCHEMA.STATISTICS 
                WHERE 
                    TABLE_SCHEMA = 'esri_test'
                    AND TABLE_NAME IN ('employee_account', 'employee_info')
                ORDER BY 
                    TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX
            """)
            indexes = cursor.fetchall()
            current_table = ""
            current_index = ""
            for idx in indexes:
                if idx[0] != current_table:
                    print(f"\n  表 {idx[0]}:")
                    current_table = idx[0]
                if idx[1] != current_index:
                    print(f"    索引 {idx[1]} ({'非唯一' if idx[3] else '唯一'}):")
                    current_index = idx[1]
                print(f"      {idx[2]}")
                
    except Exception as e:
        print(f"数据库查询错误：{str(e)}")
    finally:
        if 'connection' in locals():
            connection.close()

def check_data_consistency():
    """检查数据一致性"""
    print("\n=== 数据一致性检查 ===")
    
    try:
        connection = pymysql.connect(
            host='127.0.0.1',
            user='root',
            password='root',
            database='esri_test'
        )
        
        with connection.cursor() as cursor:
            # 检查孤立账号（有账号但没有对应员工信息）
            print("--- 孤立账号检查 ---")
            cursor.execute("""
                SELECT ea.employee_user_name, ea.employee_number 
                FROM employee_account ea 
                LEFT JOIN employee_info ei ON ea.employee_number = ei.employee_number 
                WHERE ei.employee_number IS NULL
            """)
            orphaned_accounts = cursor.fetchall()
            if orphaned_accounts:
                print("  发现孤立账号：")
                for account in orphaned_accounts:
                    print(f"    用户名：{account[0]}，员工编号：{account[1]}")
            else:
                print("  没有孤立账号")
            
            # 检查孤立员工信息（有员工信息但没有对应账号）
            print("\n--- 孤立员工信息检查 ---")
            cursor.execute("""
                SELECT ei.employee_number, ei.name 
                FROM employee_info ei 
                LEFT JOIN employee_account ea ON ei.employee_number = ea.employee_number 
                WHERE ea.employee_number IS NULL
            """)
            orphaned_info = cursor.fetchall()
            if orphaned_info:
                print("  发现孤立员工信息：")
                for info in orphaned_info:
                    print(f"    员工编号：{info[0]}，姓名：{info[1]}")
            else:
                print("  没有孤立员工信息")
                
            # 检查emp_test_2024的完整数据
            print("\n--- 测试用户数据完整性 ---")
            cursor.execute("""
                SELECT 
                    ea.employee_user_name,
                    ea.employee_number,
                    ei.name,
                    ei.employee_number as ei_employee_number
                FROM employee_account ea 
                LEFT JOIN employee_info ei ON ea.employee_number = ei.employee_number 
                WHERE ea.employee_user_name = 'emp_test_2024'
            """)
            test_user_data = cursor.fetchone()
            if test_user_data:
                print(f"  用户名：{test_user_data[0]}")
                print(f"  账号员工编号：{test_user_data[1]}")
                print(f"  员工姓名：{test_user_data[2]}")
                print(f"  信息表员工编号：{test_user_data[3]}")
                if test_user_data[1] == test_user_data[3]:
                    print("  ✅ 数据一致")
                else:
                    print("  ❌ 数据不一致")
            else:
                print("  未找到测试用户")
                
    except Exception as e:
        print(f"数据一致性检查错误：{str(e)}")
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    check_database_structure()
    check_data_consistency()
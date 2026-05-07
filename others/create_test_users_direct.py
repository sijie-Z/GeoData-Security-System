#!/usr/bin/env python3
"""
直接数据库操作创建测试用户
小白讲解：这个脚本直接连接数据库创建测试账户，避免模型冲突
"""

import pymysql
from pymysql.cursors import DictCursor
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_test_users_direct():
    """
    小白讲解：直接连接MySQL数据库创建测试用户
    """
    try:
        # 连接数据库
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='root',
            database='esri_test',
            port=3306,
            charset='utf8mb4',
            cursorclass=DictCursor
        )
        
        cursor = conn.cursor()
        
        # 检查是否已存在测试用户
        cursor.execute("SELECT COUNT(*) as count FROM employee_account WHERE employee_user_name = 'zhangsan@test.com'")
        result = cursor.fetchone()
        
        if result and result['count'] > 0:
            print("测试用户已存在，跳过创建")
            return True
        
        # 先创建员工信息记录（因为employee_account表有外键约束）
        cursor.execute("SELECT COUNT(*) as count FROM employee_info WHERE employee_number = 'EMP001'")
        emp_info_result = cursor.fetchone()
        
        if not emp_info_result or emp_info_result['count'] == 0:
            employee_info_sql = """
            INSERT INTO employee_info 
            (employee_number, name, job_number, phone_number, address, id_number, create_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            employee_info_data = (
                'EMP001',
                '张三',
                'EMP001',
                '18812345678',
                '北京市朝阳区',
                '110101199001011234',
                datetime.now()
            )
            
            cursor.execute(employee_info_sql, employee_info_data)
        
        # 创建普通员工账户
        employee_sql = """
        INSERT INTO employee_account 
        (employee_number, employee_user_name, employee_user_password, role, status, avatar, create_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        employee_data = (
            'EMP001',
            'zhangsan@test.com',
            generate_password_hash('123456'),
            'employee',
            'active',
            None,
            datetime.now()
        )
        
        cursor.execute(employee_sql, employee_data)
        
        # 先创建管理员信息记录
        cursor.execute("SELECT COUNT(*) as count FROM adm_info WHERE adm_number = 'ADM001'")
        adm_info_result = cursor.fetchone()
        
        if not adm_info_result or adm_info_result['count'] == 0:
            admin_info_sql = """
            INSERT INTO adm_info 
            (adm_number, name, job_number, phone_number, address, id_number, create_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            admin_info_data = (
                'ADM001',
                '李四管理员',
                'ADM001',
                '19912345678',
                '北京市海淀区',
                '110101198503052345',
                datetime.now()
            )
            
            cursor.execute(admin_info_sql, admin_info_data)
        
        # 创建管理员账户
        admin_sql = """
        INSERT INTO adm_account 
        (adm_number, account, adm_user_name, adm_user_password, role, status, avatar, create_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        admin_data = (
            'ADM001',
            'admin@test.com',
            '李四管理员',
            generate_password_hash('admin123'),
            'admin',
            'active',
            None,
            datetime.now()
        )
        
        cursor.execute(admin_sql, admin_data)
        
        # 提交事务
        conn.commit()
        
        print("✅ 测试用户创建成功！")
        print("普通员工账户：")
        print("- 用户名：zhangsan@test.com")
        print("- 密码：123456")
        print("- 员工编号：EMP001")
        print()
        print("管理员账户：")
        print("- 用户名：admin@test.com") 
        print("- 密码：admin123")
        print("- 管理员编号：ADM001")
        print()
        print("现在可以用这些账户测试登录功能了！")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 创建用户失败：{e}")
        return False

if __name__ == '__main__':
    create_test_users_direct()
    
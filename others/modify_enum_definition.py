#!/usr/bin/env python3
"""
修改数据库枚举定义
小白讲解：将数据库中的枚举改为ACTIVE, INACTIVE, BANNED
"""

from importlib import import_module

try:
    mysql_connector = import_module("mysql.connector")
except ModuleNotFoundError:
    mysql_connector = None

def modify_enum_definition():
    """
    小白讲解：修改数据库中的枚举定义
    """
    try:
        # 连接数据库
        if mysql_connector is None:
            raise ModuleNotFoundError(
                "未安装 mysql-connector-python。请先执行: pip install mysql-connector-python"
            )

        conn = mysql_connector.connect(
            host='localhost',
            user='root',
            password='root',
            database='esri_test',
            port=3306
        )
        
        cursor = conn.cursor()
        
        # 修改employee_account表的status字段
        cursor.execute("""
        ALTER TABLE employee_account 
        MODIFY COLUMN status ENUM('ACTIVE','INACTIVE','BANNED') DEFAULT 'ACTIVE'
        """)
        
        # 修改adm_account表的status字段
        cursor.execute("""
        ALTER TABLE adm_account 
        MODIFY COLUMN status ENUM('ACTIVE','INACTIVE','BANNED') DEFAULT 'ACTIVE'
        """)
        
        # 更新现有的数据
        cursor.execute("UPDATE employee_account SET status = 'ACTIVE' WHERE status = 'active'")
        cursor.execute("UPDATE adm_account SET status = 'ACTIVE' WHERE status = 'active'")
        
        # 提交事务
        conn.commit()
        
        print("✅ 枚举定义修改成功！")
        print("已将所有状态值改为ACTIVE, INACTIVE, BANNED")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 修改枚举定义失败：{e}")
        return False

if __name__ == '__main__':
    modify_enum_definition()
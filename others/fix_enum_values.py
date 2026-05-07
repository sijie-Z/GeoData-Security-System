#!/usr/bin/env python3
"""
修正数据库中的枚举值
小白讲解：将数据库中的状态值改为大写，匹配枚举定义
"""

import pymysql
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_enum_values():
    """
    小白讲解：修正数据库中的枚举值，改为大写
    """
    conn = None
    try:
        # 连接数据库 (使用 pymysql 保持项目一致性)
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='root',
            database='esri_test',
            port=3306,
            charset='utf8mb4'
        )
        
        cursor = conn.cursor()
        
        # 修正员工账户状态
        # 小白注意：SQL 语句中对大小写敏感，这里将存储的 'active' 统一改为 'ACTIVE'
        logger.info("正在修正 employee_account 表的状态值...")
        cursor.execute("UPDATE employee_account SET status = 'ACTIVE' WHERE status = 'active'")
        cursor.execute("UPDATE employee_account SET status = 'INACTIVE' WHERE status = 'inactive'")
        
        # 修正管理员账户状态
        logger.info("正在修正 adm_account 表的状态值...")
        cursor.execute("UPDATE adm_account SET status = 'ACTIVE' WHERE status = 'active'")
        cursor.execute("UPDATE adm_account SET status = 'INACTIVE' WHERE status = 'inactive'")
        
        # 提交事务
        conn.commit()
        
        print("✅ 枚举值修正成功！")
        print("已将所有状态值改为大写形式 (ACTIVE/INACTIVE)")
        
        cursor.close()
        return True
        
    except Exception as e:
        if conn:
            conn.rollback() # 出错时回滚
        print(f"❌ 修正枚举值失败：{e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    fix_enum_values()
    
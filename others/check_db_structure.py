#!/usr/bin/env python3
"""
数据库结构检查脚本 - 查看PostgreSQL和MySQL数据库中的表结构
小白说明：这个脚本会列出两个数据库中的所有表，帮助了解数据存储情况
"""

import psycopg2
import pymysql
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_postgres_structure():
    """检查PostgreSQL数据库结构"""
    try:
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=5432,
            database='esri_test',
            user='postgres',
            password='root'
        )
        cursor = conn.cursor()
        
        logger.info("🔍 检查PostgreSQL数据库结构...")
        
        # 获取所有表
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        logger.info(f"📊 PostgreSQL数据库 'esri_test' 中的表 ({len(tables)}个):")
        for table in tables:
            table_name = table[0]
            logger.info(f"   📋 {table_name}")
            
            # 获取表结构
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            
            for col in columns:
                logger.info(f"      - {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
            
            # 获取记录数
            try:
                cursor.execute(f'SELECT COUNT(*) FROM public."{table_name}"')
                row = cursor.fetchone()
                count = row[0] if row else 0
                logger.info(f"      📈 记录数: {count}")
            except Exception as e:
                logger.warning(f"      ⚠️ 无法获取记录数: {e}")
            
            logger.info("")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ PostgreSQL数据库检查失败: {e}")
        return False

def check_mysql_structure():
    """检查MySQL数据库结构"""
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            database='spatial_data_sys',
            user='root',
            password='root'
        )
        cursor = conn.cursor()
        
        logger.info("🔍 检查MySQL数据库结构...")
        
        # 获取所有表
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        logger.info(f"📊 MySQL数据库 'spatial_data_sys' 中的表 ({len(tables)}个):")
        for table in tables:
            table_name = table[0]
            logger.info(f"   📋 {table_name}")
            
            # 获取表结构
            cursor.execute(f"SHOW CREATE TABLE {table_name}")
            row = cursor.fetchone()
            create_statement = row[1] if row and len(row) > 1 else ""
            logger.info(f"      📐 创建语句: {create_statement[:200]}...")
            
            # 获取记录数
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                row = cursor.fetchone()
                count = row[0] if row else 0
                logger.info(f"      📈 记录数: {count}")
            except Exception as e:
                logger.warning(f"      ⚠️ 无法获取记录数: {e}")
            
            logger.info("")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ MySQL数据库检查失败: {e}")
        return False

def check_mysql_esri_test():
    """检查MySQL esri_test数据库结构"""
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            database='esri_test',
            user='root',
            password='root'
        )
        cursor = conn.cursor()
        
        logger.info("🔍 检查MySQL esri_test数据库结构...")
        
        # 获取所有表
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        logger.info(f"📊 MySQL数据库 'esri_test' 中的表 ({len(tables)}个):")
        for table in tables:
            table_name = table[0]
            logger.info(f"   📋 {table_name}")
            
            # 获取记录数
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                row = cursor.fetchone()
                count = row[0] if row else 0
                logger.info(f"      📈 记录数: {count}")
            except Exception as e:
                logger.warning(f"      ⚠️ 无法获取记录数: {e}")
            
            logger.info("")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ MySQL esri_test数据库检查失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始数据库结构检查")
    logger.info("=" * 60)
    
    # 1. 检查PostgreSQL
    check_postgres_structure()
    
    logger.info("=" * 60)
    
    # 2. 检查MySQL spatial_data_sys
    check_mysql_structure()
    
    logger.info("=" * 60)
    
    # 3. 检查MySQL esri_test
    check_mysql_esri_test()
    
    logger.info("=" * 60)
    logger.info("🔍 数据库结构检查完成！")

if __name__ == "__main__":
    main()

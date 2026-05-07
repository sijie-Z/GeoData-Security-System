#!/usr/bin/env python3
"""
MySQL表结构检查 - 查看目标数据库中的表结构
小白说明：这个脚本会检查MySQL数据库中是否有所需的表
"""

import pymysql
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_mysql_tables():
    """检查MySQL数据库中的表"""
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            database='esri_test',
            user='root',
            password='root'
        )
        cursor = conn.cursor()
        
        logger.info("🔍 检查MySQL esri_test数据库中的表...")
        
        # 获取所有表
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        logger.info(f"📊 MySQL数据库 'esri_test' 中的表 ({len(tables)}个):")
        
        # 查找与空间数据相关的表
        spatial_tables = []
        for table in tables:
            table_name = table[0]
            if any(keyword in table_name.lower() for keyword in ['shp', 'raster', 'data', 'spatial', 'geo']):
                spatial_tables.append(table_name)
                logger.info(f"   📋 {table_name} (空间数据相关)")
            else:
                logger.info(f"   📋 {table_name}")
        
        logger.info(f"\n🎯 找到 {len(spatial_tables)} 个空间数据相关表:")
        for table in spatial_tables:
            logger.info(f"   ✅ {table}")
        
        # 检查是否有类似shp_data_io的表
        shp_like_tables = [t for t in tables if 'shp' in t[0].lower()]
        raster_like_tables = [t for t in tables if 'raster' in t[0].lower()]
        
        logger.info(f"\n🔍 SHP相关表: {shp_like_tables}")
        logger.info(f"🔍 Raster相关表: {raster_like_tables}")
        
        # 检查具体的表结构
        target_tables = ['shp_data_io', 'raster_data', 'mysqlshpio', 'rasterdata']
        for table_name in target_tables:
            try:
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                logger.info(f"\n📐 {table_name} 表结构:")
                for col in columns:
                    logger.info(f"   - {col[0]}: {col[1]} (null: {col[2]}, key: {col[3]}, default: {col[4]})")
            except Exception as e:
                logger.warning(f"   ❌ {table_name} 表不存在: {e}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ MySQL数据库检查失败: {e}")
        return False

def check_mysql_spatial_data_sys():
    """检查MySQL spatial_data_sys数据库（如果存在）"""
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            database='spatial_data_sys',
            user='root',
            password='root'
        )
        cursor = conn.cursor()
        
        logger.info("\n🔍 检查MySQL spatial_data_sys数据库中的表...")
        
        # 获取所有表
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        logger.info(f"📊 MySQL数据库 'spatial_data_sys' 中的表 ({len(tables)}个):")
        for table in tables:
            table_name = table[0]
            logger.info(f"   📋 {table_name}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.info(f"ℹ️ spatial_data_sys数据库不存在或无法访问: {e}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始MySQL表结构检查")
    logger.info("=" * 60)
    
    # 1. 检查esri_test数据库
    check_mysql_tables()
    
    # 2. 检查spatial_data_sys数据库
    check_mysql_spatial_data_sys()
    
    logger.info("=" * 60)
    logger.info("🔍 MySQL表结构检查完成！")

if __name__ == "__main__":
    main()
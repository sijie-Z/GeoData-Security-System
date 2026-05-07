#!/usr/bin/env python3
"""
数据迁移脚本 - 从PostgreSQL esri_test数据库迁移ShpDataIO和RasterData数据到MySQL
小白说明：这个脚本会把原来的空间数据迁移到新的数据库中
"""

import psycopg2
import pymysql
from psycopg2.extras import RealDictCursor
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# PostgreSQL连接配置
POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'esri_test',
    'user': 'postgres',
    'password': '123456'  # 根据你的实际密码修改
}

# MySQL连接配置
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'spatial_data_sys',
    'user': 'root',
    'password': '123456'  # 根据你的实际密码修改
}

def connect_postgres():
    """连接PostgreSQL数据库"""
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        logger.info("✅ 成功连接到PostgreSQL数据库")
        return conn
    except Exception as e:
        logger.error(f"❌ 连接PostgreSQL失败: {e}")
        return None

def connect_mysql():
    """连接MySQL数据库"""
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        logger.info("✅ 成功连接到MySQL数据库")
        return conn
    except Exception as e:
        logger.error(f"❌ 连接MySQL失败: {e}")
        return None

def get_shpdata_from_postgres():
    """从PostgreSQL获取ShpDataIO数据"""
    postgres_conn = connect_postgres()
    if not postgres_conn:
        return []
    
    try:
        cursor = postgres_conn.cursor(cursor_factory=RealDictCursor)
        
        # 查询ShpDataIO表数据
        query = """
        SELECT 
            id, name, description, file_path, file_size,
            upload_time, uploaded_by, geometry_type, 
            bounding_box, attributes, status
        FROM public."ShpDataIO" 
        ORDER BY id
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        logger.info(f"📊 从PostgreSQL获取到 {len(results)} 条ShpDataIO记录")
        
        cursor.close()
        postgres_conn.close()
        
        return results
        
    except Exception as e:
        logger.error(f"❌ 查询ShpDataIO数据失败: {e}")
        return []

def get_rasterdata_from_postgres():
    """从PostgreSQL获取RasterData数据"""
    postgres_conn = connect_postgres()
    if not postgres_conn:
        return []
    
    try:
        cursor = postgres_conn.cursor(cursor_factory=RealDictCursor)
        
        # 查询RasterData表数据
        query = """
        SELECT 
            id, name, description, file_path, file_size,
            upload_time, uploaded_by, raster_type, 
            resolution, bands, bounding_box, status
        FROM public."RasterData" 
        ORDER BY id
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        logger.info(f"📊 从PostgreSQL获取到 {len(results)} 条RasterData记录")
        
        cursor.close()
        postgres_conn.close()
        
        return results
        
    except Exception as e:
        logger.error(f"❌ 查询RasterData数据失败: {e}")
        return []

def migrate_shpdata_to_mysql(shpdata_list):
    """迁移ShpDataIO数据到MySQL"""
    mysql_conn = connect_mysql()
    if not mysql_conn:
        return False
    
    try:
        cursor = mysql_conn.cursor()
        
        # 清空现有数据（谨慎操作）
        cursor.execute("TRUNCATE TABLE shp_data_io")
        mysql_conn.commit()
        logger.info("🗑️ 已清空MySQL中shp_data_io表数据")
        
        # 插入数据
        insert_query = """
        INSERT INTO shp_data_io 
        (id, name, description, file_path, file_size, upload_time, 
         uploaded_by, geometry_type, bounding_box, attributes, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        success_count = 0
        error_count = 0
        
        for data in shpdata_list:
            try:
                # 转换数据格式
                upload_time = data.get('upload_time')
                if upload_time and hasattr(upload_time, 'strftime'):
                    upload_time = upload_time.strftime('%Y-%m-%d %H:%M:%S')
                
                # 处理JSON字段
                bounding_box = json.dumps(data.get('bounding_box')) if data.get('bounding_box') else None
                attributes = json.dumps(data.get('attributes')) if data.get('attributes') else None
                
                values = (
                    data.get('id'),
                    data.get('name'),
                    data.get('description'),
                    data.get('file_path'),
                    data.get('file_size'),
                    upload_time,
                    data.get('uploaded_by'),
                    data.get('geometry_type'),
                    bounding_box,
                    attributes,
                    data.get('status', 'active')
                )
                
                cursor.execute(insert_query, values)
                success_count += 1
                
                if success_count % 100 == 0:
                    mysql_conn.commit()
                    logger.info(f"🔄 已迁移 {success_count} 条ShpDataIO记录")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"❌ 插入ShpDataIO记录失败 (ID: {data.get('id')}): {e}")
                continue
        
        mysql_conn.commit()
        
        logger.info(f"✅ ShpDataIO数据迁移完成：成功 {success_count} 条，失败 {error_count} 条")
        
        cursor.close()
        mysql_conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 迁移ShpDataIO数据失败: {e}")
        return False

def migrate_rasterdata_to_mysql(rasterdata_list):
    """迁移RasterData数据到MySQL"""
    mysql_conn = connect_mysql()
    if not mysql_conn:
        return False
    
    try:
        cursor = mysql_conn.cursor()
        
        # 清空现有数据（谨慎操作）
        cursor.execute("TRUNCATE TABLE raster_data")
        mysql_conn.commit()
        logger.info("🗑️ 已清空MySQL中raster_data表数据")
        
        # 插入数据
        insert_query = """
        INSERT INTO raster_data 
        (id, name, description, file_path, file_size, upload_time, 
         uploaded_by, raster_type, resolution, bands, bounding_box, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        success_count = 0
        error_count = 0
        
        for data in rasterdata_list:
            try:
                # 转换数据格式
                upload_time = data.get('upload_time')
                if upload_time and hasattr(upload_time, 'strftime'):
                    upload_time = upload_time.strftime('%Y-%m-%d %H:%M:%S')
                
                # 处理JSON字段
                resolution = json.dumps(data.get('resolution')) if data.get('resolution') else None
                bounding_box = json.dumps(data.get('bounding_box')) if data.get('bounding_box') else None
                
                values = (
                    data.get('id'),
                    data.get('name'),
                    data.get('description'),
                    data.get('file_path'),
                    data.get('file_size'),
                    upload_time,
                    data.get('uploaded_by'),
                    data.get('raster_type'),
                    resolution,
                    data.get('bands'),
                    bounding_box,
                    data.get('status', 'active')
                )
                
                cursor.execute(insert_query, values)
                success_count += 1
                
                if success_count % 100 == 0:
                    mysql_conn.commit()
                    logger.info(f"🔄 已迁移 {success_count} 条RasterData记录")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"❌ 插入RasterData记录失败 (ID: {data.get('id')}): {e}")
                continue
        
        mysql_conn.commit()
        
        logger.info(f"✅ RasterData数据迁移完成：成功 {success_count} 条，失败 {error_count} 条")
        
        cursor.close()
        mysql_conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 迁移RasterData数据失败: {e}")
        return False

def verify_migration():
    """验证数据迁移结果"""
    mysql_conn = connect_mysql()
    if not mysql_conn:
        return False
    
    try:
        cursor = mysql_conn.cursor()
        
        # 统计ShpDataIO数据
        cursor.execute("SELECT COUNT(*) as count FROM shp_data_io")
        shp_row = cursor.fetchone()
        shp_count = shp_row[0] if shp_row else 0
        
        # 统计RasterData数据
        cursor.execute("SELECT COUNT(*) as count FROM raster_data")
        raster_row = cursor.fetchone()
        raster_count = raster_row[0] if raster_row else 0
        
        logger.info(f"📊 数据迁移验证结果：")
        logger.info(f"   ShpDataIO记录数: {shp_count}")
        logger.info(f"   RasterData记录数: {raster_count}")
        
        # 显示前几条数据作为样本
        cursor.execute("SELECT id, name, upload_time FROM shp_data_io ORDER BY id LIMIT 3")
        shp_samples = cursor.fetchall()
        logger.info(f"   ShpDataIO样本数据: {shp_samples}")
        
        cursor.execute("SELECT id, name, upload_time FROM raster_data ORDER BY id LIMIT 3")
        raster_samples = cursor.fetchall()
        logger.info(f"   RasterData样本数据: {raster_samples}")
        
        cursor.close()
        mysql_conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据验证失败: {e}")
        return False

def main():
    """主函数 - 执行数据迁移"""
    logger.info("🚀 开始数据迁移任务")
    logger.info("=" * 50)
    
    # 1. 从PostgreSQL获取数据
    logger.info("📥 开始从PostgreSQL获取数据...")
    shpdata_list = get_shpdata_from_postgres()
    rasterdata_list = get_rasterdata_from_postgres()
    
    if not shpdata_list and not rasterdata_list:
        logger.error("❌ 未能从PostgreSQL获取到任何数据，迁移终止")
        return
    
    # 2. 迁移ShpDataIO数据
    if shpdata_list:
        logger.info("🔄 开始迁移ShpDataIO数据...")
        migrate_shpdata_to_mysql(shpdata_list)
    
    # 3. 迁移RasterData数据
    if rasterdata_list:
        logger.info("🔄 开始迁移RasterData数据...")
        migrate_rasterdata_to_mysql(rasterdata_list)
    
    # 4. 验证迁移结果
    logger.info("🔍 开始验证迁移结果...")
    verify_migration()
    
    logger.info("=" * 50)
    logger.info("🎉 数据迁移任务完成！")

if __name__ == "__main__":
    main()
    
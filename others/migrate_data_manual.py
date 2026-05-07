#!/usr/bin/env python3
"""
手动数据库迁移脚本 - 允许你输入正确的数据库连接信息
小白说明：这个脚本会让你手动输入数据库连接信息，然后执行数据迁移
"""

import psycopg2
import pymysql
from psycopg2.extras import RealDictCursor
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_user_input():
    """获取用户输入的数据库连接信息"""
    print("🎯 请输入数据库连接信息：")
    print("=" * 50)
    
    # PostgreSQL连接信息
    print("📊 PostgreSQL数据库 (esri_test)：")
    pg_host = input("   主机地址 [localhost]: ").strip() or "localhost"
    pg_port = input("   端口[5432]: ").strip() or "5432"
    pg_database = input("   数据库名 [esri_test]: ").strip() or "esri_test"
    pg_user = input("   用户名 [postgres]: ").strip() or "postgres"
    pg_password = input("   密码: ").strip()
    
    print()
    
    # MySQL连接信息
    print("🗄️ MySQL数据库 (spatial_data_sys)：")
    mysql_host = input("   主机地址[localhost]: ").strip() or "localhost"
    mysql_port = input("   端口 [3306]: ").strip() or "3306"
    mysql_database = input("   数据库名[spatial_data_sys]: ").strip() or "spatial_data_sys"
    mysql_user = input("   用户名 [root]: ").strip() or "root"
    mysql_password = input("   密码: ").strip()
    
    return {
        'postgres': {
            'host': pg_host,
            'port': int(pg_port),
            'database': pg_database,
            'user': pg_user,
            'password': pg_password
        },
        'mysql': {
            'host': mysql_host,
            'port': int(mysql_port),
            'database': mysql_database,
            'user': mysql_user,
            'password': mysql_password
        }
    }

def test_connections(config):
    """测试数据库连接"""
    print("\n🔍 测试数据库连接...")
    print("=" * 50)
    
    # 测试PostgreSQL
    try:
        pg_conn = psycopg2.connect(**config['postgres'])
        pg_conn.close()
        print("✅ PostgreSQL连接成功！")
    except Exception as e:
        print(f"❌ PostgreSQL连接失败: {e}")
        return False
    
    # 测试MySQL
    try:
        mysql_conn = pymysql.connect(**config['mysql'])
        mysql_conn.close()
        print("✅ MySQL连接成功！")
    except Exception as e:
        print(f"❌ MySQL连接失败: {e}")
        return False
    
    return True

def get_shpdata_from_postgres(config):
    """从PostgreSQL获取ShpDataIO数据"""
    try:
        conn = psycopg2.connect(**config['postgres'])
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
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
        conn.close()
        
        return results
        
    except Exception as e:
        logger.error(f"❌ 查询ShpDataIO数据失败: {e}")
        return[]

def get_rasterdata_from_postgres(config):
    """从PostgreSQL获取RasterData数据"""
    try:
        conn = psycopg2.connect(**config['postgres'])
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
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
        conn.close()
        
        return results
        
    except Exception as e:
        logger.error(f"❌ 查询RasterData数据失败: {e}")
        return[]

def migrate_shpdata_to_mysql(shpdata_list, config):
    """迁移ShpDataIO数据到MySQL"""
    try:
        conn = pymysql.connect(**config['mysql'])
        cursor = conn.cursor()
        
        # 清空现有数据（谨慎操作）
        cursor.execute("TRUNCATE TABLE shp_data_io")
        conn.commit()
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
                if upload_time:
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
                    conn.commit()
                    logger.info(f"🔄 已迁移 {success_count} 条ShpDataIO记录")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"❌ 插入ShpDataIO记录失败 (ID: {data.get('id')}): {e}")
                continue
        
        conn.commit()
        
        logger.info(f"✅ ShpDataIO数据迁移完成：成功 {success_count} 条，失败 {error_count} 条")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 迁移ShpDataIO数据失败: {e}")
        return False

def migrate_rasterdata_to_mysql(rasterdata_list, config):
    """迁移RasterData数据到MySQL"""
    try:
        conn = pymysql.connect(**config['mysql'])
        cursor = conn.cursor()
        
        # 清空现有数据（谨慎操作）
        cursor.execute("TRUNCATE TABLE raster_data")
        conn.commit()
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
                if upload_time:
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
                    conn.commit()
                    logger.info(f"🔄 已迁移 {success_count} 条RasterData记录")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"❌ 插入RasterData记录失败 (ID: {data.get('id')}): {e}")
                continue
        
        conn.commit()
        
        logger.info(f"✅ RasterData数据迁移完成：成功 {success_count} 条，失败 {error_count} 条")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 迁移RasterData数据失败: {e}")
        return False

def verify_migration(config):
    """验证数据迁移结果"""
    try:
        conn = pymysql.connect(**config['mysql'])
        cursor = conn.cursor()
        
        # 统计ShpDataIO数据
        cursor.execute("SELECT COUNT(*) as count FROM shp_data_io")
        shp_result = cursor.fetchone()
        shp_count = shp_result[0] if shp_result else 0
        
        # 统计RasterData数据
        cursor.execute("SELECT COUNT(*) as count FROM raster_data")
        raster_result = cursor.fetchone()
        raster_count = raster_result[0] if raster_result else 0
        
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
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据验证失败: {e}")
        return False

def main():
    """主函数 - 执行数据迁移"""
    print("🚀 开始数据迁移任务")
    print("=" * 60)
    
    # 1. 获取用户输入的连接信息
    config = get_user_input()
    
    # 2. 测试连接
    if not test_connections(config):
        print("❌ 数据库连接测试失败，请检查输入的信息")
        return
    
    print("\n🔄 开始执行数据迁移...")
    print("=" * 60)
    
    # 3. 从PostgreSQL获取数据
    logger.info("📥 开始从PostgreSQL获取数据...")
    shpdata_list = get_shpdata_from_postgres(config)
    rasterdata_list = get_rasterdata_from_postgres(config)
    
    if not shpdata_list and not rasterdata_list:
        logger.error("❌ 未能从PostgreSQL获取到任何数据，迁移终止")
        return
    
    # 4. 迁移ShpDataIO数据
    if shpdata_list:
        logger.info("🔄 开始迁移ShpDataIO数据...")
        migrate_shpdata_to_mysql(shpdata_list, config)
    
    # 5. 迁移RasterData数据
    if rasterdata_list:
        logger.info("🔄 开始迁移RasterData数据...")
        migrate_rasterdata_to_mysql(rasterdata_list, config)
    
    # 6. 验证迁移结果
    logger.info("🔍 开始验证迁移结果...")
    verify_migration(config)
    
    print("=" * 60)
    print("🎉 数据迁移任务完成！")
    print("💡 你现在可以在新的系统中查看迁移过来的空间数据了")

if __name__ == "__main__":
    main()
    
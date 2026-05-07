#!/usr/bin/env python3
"""
简化数据迁移脚本 - 使用配置字典
小白说明：这个脚本会尝试常见的数据库连接配置
"""

import psycopg2
import pymysql
from psycopg2.extras import RealDictCursor
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库连接配置 - 使用项目中的实际配置
DB_CONFIGS = {
    'postgres': [
        {'host': '127.0.0.1', 'port': 5432, 'database': 'esri_test', 'user': 'postgres', 'password': 'root'},
    ],
    'mysql': [
        {'host': '127.0.0.1', 'port': 3306, 'database': 'esri_test', 'user': 'root', 'password': 'root'},
        {'host': '127.0.0.1', 'port': 3306, 'database': 'spatial_data_sys', 'user': 'root', 'password': 'root'},
    ]
}

def test_postgres_connection(config):
    """测试PostgreSQL连接"""
    try:
        conn = psycopg2.connect(**config)
        conn.close()
        logger.info(f"✅ PostgreSQL连接成功: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
        return True
    except Exception as e:
        logger.debug(f"❌ PostgreSQL连接失败: {e}")
        return False

def test_mysql_connection(config):
    """测试MySQL连接"""
    try:
        conn = pymysql.connect(**config)
        conn.close()
        logger.info(f"✅ MySQL连接成功: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
        return True
    except Exception as e:
        logger.debug(f"❌ MySQL连接失败: {e}")
        return False

def find_working_config():
    """找到可用的数据库连接配置"""
    logger.info("🔍 正在寻找可用的数据库连接配置...")
    
    postgres_config = None
    mysql_config = None
    
    # 测试PostgreSQL配置
    for config in DB_CONFIGS['postgres']:
        if test_postgres_connection(config):
            postgres_config = config
            break
    
    # 测试MySQL配置
    for config in DB_CONFIGS['mysql']:
        if test_mysql_connection(config):
            mysql_config = config
            break
    
    return postgres_config, mysql_config

def get_shpdata_from_postgres(config):
    """从PostgreSQL获取ShpDataIO数据"""
    try:
        conn = psycopg2.connect(**config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 首先检查表是否存在
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'ShpDataIO'
            )
        """)
        result = cursor.fetchone()
        table_exists = result['exists'] if result else False
        
        if not table_exists:
            logger.warning("⚠️ PostgreSQL中ShpDataIO表不存在")
            return []
        
        # 查询ShpDataIO表数据 - 使用实际的字段结构
        query = """
        SELECT 
            id, name, alias, geomtype, introduction,
            datetime, url, layer, shp_file_path, uuid,
            coordinate_system, data_source
        FROM public."ShpDataIO" 
        ORDER BY id
        """
        
        logger.info(f"📝 执行查询: {query}")
        cursor.execute(query)
        results = cursor.fetchall()
        
        logger.info(f"📊 从PostgreSQL获取到 {len(results)} 条ShpDataIO记录")
        
        # 显示第一条记录作为样本
        if results:
            logger.info(f"🔍 样本记录: {results[0]}")
        
        cursor.close()
        conn.close()
        
        return results
        
    except Exception as e:
        logger.error(f"❌ 查询ShpDataIO数据失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return []

def get_rasterdata_from_postgres(config):
    """从PostgreSQL获取RasterData数据"""
    try:
        conn = psycopg2.connect(**config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 首先检查表是否存在
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'RasterData'
            )
        """)
        result = cursor.fetchone()
        table_exists = result['exists'] if result else False
        
        if not table_exists:
            logger.warning("⚠️ PostgreSQL中RasterData表不存在")
            return []
        
        # 查询RasterData表数据 - 使用实际的字段结构
        query = """
        SELECT 
            id, name, alias, bands, resolution, introduction,
            datetime, url, layer, file_path, uuid,
            coordinate_system, data_source
        FROM public."RasterData" 
        ORDER BY id
        """
        
        logger.info(f"📝 执行查询: {query}")
        cursor.execute(query)
        results = cursor.fetchall()
        
        logger.info(f"📊 从PostgreSQL获取到 {len(results)} 条RasterData记录")
        
        # 显示第一条记录作为样本
        if results:
            logger.info(f"🔍 样本记录: {results[0]}")
        
        cursor.close()
        conn.close()
        
        return results
        
    except Exception as e:
        logger.error(f"❌ 查询RasterData数据失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return []

def migrate_shpdata_to_mysql(shpdata_list, config):
    """迁移ShpDataIO数据到MySQL"""
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        # 清空现有数据（谨慎操作）
        cursor.execute("TRUNCATE TABLE mysqlshpio")
        conn.commit()
        logger.info("🗑️ 已清空MySQL中mysqlshpio表数据")
        
        # 插入数据 - 使用实际的字段映射
        insert_query = """
        INSERT INTO mysqlshpio 
        (id, name, alias, geomtype, introduction, datetime, url, layer, shp_file_path, coordinate_system, data_source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        success_count = 0
        error_count = 0
        
        for data in shpdata_list:
            try:
                # 转换数据格式 - 使用PostgreSQL中的实际字段名
                upload_time = data.get('datetime')
                if upload_time:
                    upload_time = upload_time.strftime('%Y-%m-%d %H:%M:%S')
                
                shp_file_path = data.get('shp_file_path')
                
                values = (
                    data.get('id'),
                    data.get('name'),
                    data.get('alias'),
                    data.get('geomtype'),
                    data.get('introduction'),
                    upload_time,
                    data.get('url'),
                    data.get('layer'),
                    shp_file_path,
                    data.get('coordinate_system'),
                    data.get('data_source')
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
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        # 清空现有数据（谨慎操作）
        cursor.execute("TRUNCATE TABLE raster_data")
        conn.commit()
        logger.info("🗑️ 已清空MySQL中raster_data表数据")
        
        # 插入数据 - 使用实际的字段映射
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
                # 转换数据格式 - 使用PostgreSQL中的实际字段名
                upload_time = data.get('datetime')
                if upload_time:
                    upload_time = upload_time.strftime('%Y-%m-%d %H:%M:%S')
                
                values = (
                    data.get('id'),
                    data.get('name'),
                    data.get('introduction'),  # 使用introduction作为description
                    data.get('file_path'),
                    None,                      # file_size - PostgreSQL中没有
                    upload_time,
                    data.get('data_source'),   # 使用data_source作为uploaded_by
                    data.get('layer'),         # 使用layer作为raster_type
                    data.get('resolution'),
                    data.get('bands'),
                    None,                      # bounding_box - PostgreSQL中没有
                    'active'                   # 默认状态
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
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        # 统计ShpDataIO数据
        cursor.execute("SELECT COUNT(*) as count FROM shp_data_io")
        shp_row = cursor.fetchone()
        shp_count = shp_row[0] if shp_row is not None else 0

        # 统计RasterData数据
        cursor.execute("SELECT COUNT(*) as count FROM raster_data")
        raster_row = cursor.fetchone()
        raster_count = raster_row[0] if raster_row is not None else 0
        
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
    logger.info("🚀 开始数据迁移任务")
    logger.info("=" * 60)
    
    # 1. 找到可用的数据库连接配置
    postgres_config, mysql_config = find_working_config()
    
    if not postgres_config:
        logger.error("❌ 未能找到可用的PostgreSQL连接配置")
        return
    
    if not mysql_config:
        logger.error("❌ 未能找到可用的MySQL连接配置")
        return
    
    logger.info("=" * 60)
    logger.info("🔄 开始执行数据迁移...")
    
    # 2. 从PostgreSQL获取数据
    logger.info("📥 开始从PostgreSQL获取数据...")
    shpdata_list = get_shpdata_from_postgres(postgres_config)
    rasterdata_list = get_rasterdata_from_postgres(postgres_config)
    
    if not shpdata_list and not rasterdata_list:
        logger.error("❌ 未能从PostgreSQL获取到任何数据，迁移终止")
        return
    
    # 3. 迁移ShpDataIO数据
    if shpdata_list:
        logger.info("🔄 开始迁移ShpDataIO数据...")
        migrate_shpdata_to_mysql(shpdata_list, mysql_config)
    
    # 4. 迁移RasterData数据
    if rasterdata_list:
        logger.info("🔄 开始迁移RasterData数据...")
        migrate_rasterdata_to_mysql(rasterdata_list, mysql_config)
    
    # 5. 验证迁移结果
    logger.info("🔍 开始验证迁移结果...")
    verify_migration(mysql_config)
    
    logger.info("=" * 60)
    logger.info("🎉 数据迁移任务完成！")
    logger.info("💡 你现在可以在新的系统中查看迁移过来的空间数据了")

if __name__ == "__main__":
    main()
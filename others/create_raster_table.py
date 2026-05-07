#!/usr/bin/env python3
"""
创建raster_data表 - 使用Python执行SQL
小白说明：这个脚本会在MySQL数据库中创建raster_data表
"""

import pymysql
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_raster_table():
    """创建raster_data表"""
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            database='esri_test',
            user='root',
            password='root'
        )
        cursor = conn.cursor()
        
        # 创建raster_data表的SQL
        create_sql = """
        CREATE TABLE IF NOT EXISTS `raster_data` (
          `id` int NOT NULL AUTO_INCREMENT,
          `name` varchar(255) DEFAULT NULL,
          `description` varchar(255) DEFAULT NULL,
          `file_path` varchar(255) DEFAULT NULL,
          `file_size` bigint DEFAULT NULL,
          `upload_time` datetime DEFAULT NULL,
          `uploaded_by` varchar(255) DEFAULT NULL,
          `raster_type` varchar(255) DEFAULT NULL,
          `resolution` varchar(255) DEFAULT NULL,
          `bands` int DEFAULT NULL,
          `bounding_box` json DEFAULT NULL,
          `attributes` json DEFAULT NULL,
          `status` varchar(50) DEFAULT 'active',
          PRIMARY KEY (`id`),
          KEY `idx_name` (`name`),
          KEY `idx_upload_time` (`upload_time`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        
        logger.info("🔨 创建raster_data表...")
        cursor.execute(create_sql)
        conn.commit()
        
        logger.info("✅ raster_data表创建成功！")
        
        # 检查表是否创建成功
        cursor.execute("SHOW TABLES LIKE 'raster_data'")
        result = cursor.fetchone()
        
        if result:
            logger.info("✅ 确认raster_data表已存在")
            
            # 显示表结构
            cursor.execute("DESCRIBE raster_data")
            columns = cursor.fetchall()
            logger.info("📋 raster_data表结构:")
            for col in columns:
                logger.info(f"   - {col[0]}: {col[1]} (null: {col[2]}, key: {col[3]})")
        else:
            logger.warning("⚠️ raster_data表可能未创建成功")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 创建raster_data表失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始创建raster_data表")
    logger.info("=" * 50)
    
    success = create_raster_table()
    
    logger.info("=" * 50)
    if success:
        logger.info("🎉 raster_data表创建完成！")
    else:
        logger.error("❌ raster_data表创建失败")

if __name__ == "__main__":
    main()
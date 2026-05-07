#!/usr/bin/env python3
"""
创建系统日志表的脚本
小白说明：这个脚本用来创建系统日志表并插入示例数据
"""

import sys
from pathlib import Path
from datetime import datetime

# 将项目根目录加入 Python 路径，确保可导入 testrealend 包
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from testrealend.extension.extension import db
from testrealend.model import SystemLog
from testrealend.app import app


def create_system_logs():
    """创建系统日志数据"""
    print("=== 开始创建系统日志数据 ===")

    with app.app_context():
        try:
            # 创建表结构
            print("正在创建系统日志表...")
            db.create_all(bind_key='mysql_db')
            print("✅ 系统日志表创建成功")

            # 检查是否已有数据
            existing_count = SystemLog.query.count()
            if existing_count > 0:
                print(f"数据库中已有 {existing_count} 条系统日志数据")
                return True

            print("正在创建示例日志数据...")

            # 创建示例日志数据
            sample_logs = [
                {
                    'user_number': 'admin001',
                    'user_name': '系统管理员',
                    'operation_type': '用户登录',
                    'operation_description': '管理员登录系统',
                    'operation_ip': '127.0.0.1',
                    'operation_status': True,
                    'operation_time': datetime.now()
                },
                {
                    'user_number': 'emp001',
                    'user_name': '张三',
                    'operation_type': '提交数据申请',
                    'operation_description': '申请下载长江流域水系数据',
                    'operation_ip': '192.168.1.100',
                    'operation_status': True,
                    'operation_time': datetime.now()
                },
                {
                    'user_number': 'admin002',
                    'user_name': '审核员',
                    'operation_type': '审批数据申请',
                    'operation_description': '批准张三的数据申请',
                    'operation_ip': '127.0.0.1',
                    'operation_status': True,
                    'operation_time': datetime.now()
                },
                {
                    'user_number': 'emp002',
                    'user_name': '李四',
                    'operation_type': '用户登录',
                    'operation_description': '员工登录系统',
                    'operation_ip': '192.168.1.101',
                    'operation_status': True,
                    'operation_time': datetime.now()
                },
                {
                    'user_number': 'admin001',
                    'user_name': '系统管理员',
                    'operation_type': '生成水印',
                    'operation_description': '为苏州市商业区划数据生成水印',
                    'operation_ip': '127.0.0.1',
                    'operation_status': True,
                    'operation_time': datetime.now()
                }
            ]

            for log_data in sample_logs:
                log = SystemLog(**log_data)
                db.session.add(log)

            db.session.commit()
            print("✅ 示例日志数据创建成功")

            # 验证数据
            new_count = SystemLog.query.count()
            print(f"新的系统日志总记录数: {new_count}")

            # 显示前几条记录
            logs = SystemLog.query.limit(3).all()
            print("\n前3条系统日志记录:")
            for log in logs:
                print(f"ID: {log.id}, 用户: {log.user_name}, 操作: {log.operation_type}, 时间: {log.operation_time}")

        except Exception as e:
            print(f"❌ 创建系统日志时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    print("=== 系统日志创建完成 ===")
    return True


if __name__ == "__main__":
    create_system_logs()

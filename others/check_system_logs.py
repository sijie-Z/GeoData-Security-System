#!/usr/bin/env python3
"""
检查系统日志数据的脚本
小白说明：这个脚本用来检查数据库中是否有系统日志数据
"""

import sys
import os

# 让脚本可从项目任意位置启动
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from testrealend.extension.extension import db
from testrealend.model import SystemLog
from testrealend.app import get_app

app = get_app()

def check_system_logs():
    """检查系统日志数据"""
    print("=== 开始检查系统日志数据 ===")
    
    with app.app_context():
        try:
            # 检查总记录数
            total_count = SystemLog.query.count()
            print(f"系统日志总记录数: {total_count}")
            
            if total_count == 0:
                print("⚠️ 数据库中没有系统日志数据")
                print("正在创建一些示例日志数据...")
                
                # 创建示例日志数据
                sample_logs = [
                    {
                        'user_number': 'admin001',
                        'user_name': '系统管理员',
                        'operation_type': '用户登录',
                        'operation_description': '管理员登录系统',
                        'operation_ip': '127.0.0.1',
                        'operation_status': True
                    },
                    {
                        'user_number': 'emp001',
                        'user_name': '张三',
                        'operation_type': '提交数据申请',
                        'operation_description': '申请下载长江流域水系数据',
                        'operation_ip': '192.168.1.100',
                        'operation_status': True
                    },
                    {
                        'user_number': 'admin002',
                        'user_name': '审核员',
                        'operation_type': '审批数据申请',
                        'operation_description': '批准张三的数据申请',
                        'operation_ip': '127.0.0.1',
                        'operation_status': True
                    }
                ]
                
                for log_data in sample_logs:
                    log = SystemLog(**log_data)
                    db.session.add(log)
                
                db.session.commit()
                print("✅ 示例日志数据创建成功")
                
                # 再次检查记录数
                new_count = SystemLog.query.count()
                print(f"新的系统日志总记录数: {new_count}")
                
            else:
                print("✅ 数据库中已有系统日志数据")
                
                # 显示前5条记录
                logs = SystemLog.query.limit(5).all()
                print("\n前5条系统日志记录:")
                for log in logs:
                    print(f"ID: {log.id}, 用户: {log.user_name}, 操作: {log.operation_type}, 时间: {log.operation_time}")
                    
        except Exception as e:
            print(f"❌ 检查系统日志时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
    print("=== 系统日志检查完成 ===")
    return True

if __name__ == "__main__":
    check_system_logs()
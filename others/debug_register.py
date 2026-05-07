#!/usr/bin/env python3
"""
调试注册功能 - 小白说明：
这个脚本用来调试前端注册失败的问题，模拟真实的FormData请求。
"""

import requests
import json
from datetime import datetime
import random

def debug_registration():
    """调试注册功能 - 模拟前端真实的FormData请求"""
    
    # 生成测试数据
    test_data = {
        'name': f'测试用户{random.randint(100, 999)}',
        'employeeId': f'test_{datetime.now().strftime("%m%d%H%M%S")}',
        'idNumber': f'32012319900101{random.randint(1000, 9999)}',
        'phone': f'138{random.randint(10000000, 99999999)}',
        'password': '123456',
        'confirmPassword': '123456'
    }
    
    print("🧪 开始调试注册功能...")
    print(f"测试数据: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
    
    # 测试1: 使用JSON格式（简单测试）
    print("\n" + "="*60)
    print("测试1: JSON格式注册")
    try:
        response = requests.post(
            'http://127.0.0.1:5001/api/register',
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 201:
            print("✅ JSON格式注册成功！")
        else:
            print(f"❌ JSON格式注册失败: {response.json().get('message', '未知错误')}")
            
    except Exception as e:
        print(f"❌ JSON测试出错: {str(e)}")
    
    # 测试2: 使用FormData格式（模拟前端真实请求）
    print("\n" + "="*60)
    print("测试2: FormData格式注册（模拟前端）")
    
    # 生成新的测试数据避免重复
    form_data = {
        'name': f'FormData用户{random.randint(100, 999)}',
        'employeeId': f'form_{datetime.now().strftime("%m%d%H%M%S")}',
        'idNumber': f'32012319900102{random.randint(1000, 9999)}',
        'phone': f'139{random.randint(10000000, 99999999)}',
        'password': '123456',
        'confirmPassword': '123456'
    }
    
    try:
        # 使用files参数来模拟multipart/form-data
        response = requests.post(
            'http://127.0.0.1:5001/api/register',
            data=form_data,
            # 不要手动设置Content-Type，让requests自动处理
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 201:
            print("✅ FormData格式注册成功！")
            return True
        else:
            print(f"❌ FormData格式注册失败: {response.json().get('message', '未知错误')}")
            return False
            
    except Exception as e:
        print(f"❌ FormData测试出错: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 开始调试注册功能...")
    print("="*60)
    
    success = debug_registration()
    
    print("\n" + "="*60)
    if success:
        print("🎉 注册功能调试成功！问题可能在前端请求方式。")
    else:
        print("⚠️  注册功能仍有问题，需要进一步调试。")
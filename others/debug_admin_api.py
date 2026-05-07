#!/usr/bin/env python3
"""
调试管理员员工管理API - 小白说明：
这个脚本用来调试管理员获取员工列表的500错误。
"""

import requests

def debug_admin_employee_api():
    """调试管理员员工管理API"""
    
    print("🔍 开始调试管理员员工管理API...")
    print("="*60)
    
    # 测试获取员工列表API
    print("测试: GET /api/adm/get_emp_info_list")
    try:
        response = requests.get(
            'http://127.0.0.1:5001/api/adm/get_emp_info_list',
            timeout=10
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text[:500]}...")  # 只显示前500字符
        
        if response.status_code == 200:
            print("✅ API调用成功！")
            data = response.json()
            print(f"返回数据条数: {len(data.get('data', []))}")
        else:
            print(f"❌ API调用失败: {response.status_code}")
            if response.headers.get('content-type', '').startswith('application/json'):
                error_data = response.json()
                print(f"错误信息: {error_data.get('message', '未知错误')}")
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败，请确保后端服务正在运行")
    except Exception as e:
        print(f"❌ 测试过程出错: {str(e)}")

if __name__ == "__main__":
    debug_admin_employee_api()
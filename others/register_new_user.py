#!/usr/bin/env python3
"""
重新注册测试
小白说明：重新注册一个测试账号
"""

import requests

def register_new_user():
    """注册新用户"""
    url = "http://localhost:5001/api/register"
    
    # 测试数据 - 使用全新的信息
    test_data = {
        "name": "李四",
        "employeeId": "emp_test_2024",
        "idNumber": "110105199003079999",  # 新的身份证号
        "phone": "13912345678",
        "password": "123456",
        "confirmPassword": "123456"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print(f"正在注册新用户...")
        print(f"员工编号: {test_data['employeeId']}")
        print(f"姓名: {test_data['name']}")
        
        response = requests.post(url, json=test_data, headers=headers)
        
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 201:
            print("✅ 注册成功！")
            return True
        else:
            print(f"❌ 注册失败")
            return False
            
    except Exception as e:
        print(f"❌ 注册失败: {e}")
        return False

if __name__ == "__main__":
    print("=== 注册新用户 ===")
    register_new_user()
    print("\n=== 完成 ===")
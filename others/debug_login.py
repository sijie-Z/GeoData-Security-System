#!/usr/bin/env python3
"""
登录测试脚本 - 小白专用
用于检查登录功能的问题
"""

import requests

def test_login():
    """测试登录功能"""
    
    # 测试用的用户信息 - 从数据库查询结果
    test_username = "emp_test_2024"
    test_password = "123456"  # 这是注册时使用的密码
    
    print(f"=== 开始测试登录功能 ===")
    print(f"测试用户：{test_username}")
    print(f"测试密码：{test_password}")
    
    # 1. 测试登录
    print("\n--- 1. 用户登录 ---")
    login_data = {
        "username": test_username,
        "password": test_password,
        "role": "employee"  # 添加角色信息
    }
    
    try:
        # 尝试JSON格式
        print("尝试JSON格式登录...")
        login_response = requests.post(
            "http://localhost:5001/api/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"JSON登录状态码：{login_response.status_code}")
        print(f"JSON登录响应：{login_response.text}")
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            token = login_result.get("access_token")  # 修正：使用access_token而不是token
            print(f"登录成功，获取到token：{token[:20]}...")
            return token
        else:
            # 尝试FormData格式
            print("\n尝试FormData格式登录...")
            form_data = {
                "username": test_username,
                "password": test_password,
                "role": "employee"
            }
            
            form_response = requests.post(
                "http://localhost:5001/api/login",
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            print(f"FormData登录状态码：{form_response.status_code}")
            print(f"FormData登录响应：{form_response.text}")
            
            if form_response.status_code == 200:
                form_result = form_response.json()
                token = form_result.get("access_token")  # 修正：使用access_token而不是token
                print(f"登录成功，获取到token：{token[:20]}...")
                return token
            else:
                print(f"登录失败，请检查用户名和密码是否正确")
                return None
            
    except Exception as e:
        print(f"测试过程中出现错误：{str(e)}")
        return None

def test_with_different_passwords():
    """尝试不同的密码组合"""
    test_username = "emp_test_2024"
    passwords_to_try = ["123456", "12345678", "password", "test123"]
    
    print(f"\n=== 尝试不同密码 ===")
    
    for password in passwords_to_try:
        print(f"\n尝试密码：{password}")
        login_data = {
            "username": test_username,
            "password": password
        }
        
        try:
            response = requests.post(
                "http://localhost:5001/api/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            print(f"状态码：{response.status_code}")
            if response.status_code == 200:
                print(f"✅ 密码正确：{password}")
                return password
            else:
                print(f"❌ 密码错误：{password}")
        except Exception as e:
            print(f"错误：{str(e)}")
    
    print("所有密码都失败了")
    return None

if __name__ == "__main__":
    token = test_login()
    if not token:
        test_with_different_passwords()
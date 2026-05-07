#!/usr/bin/env python3
"""
个人中心调试脚本 - 小白专用
用于检查个人中心API的问题
"""

import requests
import json

def test_personal_center():
    """测试个人中心功能"""
    
    # 测试用的用户信息
    test_username = "emp_test_2024"
    test_password = "123456"
    
    print(f"=== 开始测试个人中心功能 ===")
    print(f"测试用户：{test_username}")
    
    # 1. 先登录获取token
    print("\n--- 1. 用户登录 ---")
    login_data = {
        "username": test_username,
        "password": test_password,
        "role": "employee"
    }
    
    try:
        login_response = requests.post(
            "http://localhost:5001/api/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"登录状态码：{login_response.status_code}")
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            token = login_result.get("access_token")
            print(f"登录成功，获取到token：{token[:20]}...")
            
            # 2. 测试获取个人资料
            print("\n--- 2. 获取个人资料 ---")
            profile_response = requests.get(
                "http://localhost:5001/api/employee/profile",  # 修正：使用正确的API端点
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            print(f"获取个人资料状态码：{profile_response.status_code}")
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                print(f"个人资料：{json.dumps(profile_data, ensure_ascii=False, indent=2)}")
            else:
                print(f"获取个人资料失败：{profile_response.text}")
                print(f"状态码：{profile_response.status_code}")
                # 尝试获取更详细的错误信息
                try:
                    error_data = profile_response.json()
                    print(f"错误详情：{json.dumps(error_data, ensure_ascii=False, indent=2)}")
                except:
                    print(f"原始错误文本：{profile_response.text}")
                
            # 3. 测试获取员工信息 - 使用查询参数而不是路径参数
            print("\n--- 3. 测试获取员工信息 ---")
            emp_info_response = requests.get(
                f"http://localhost:5001/api/employee/info?employee_number={test_username}",  # 修正：使用查询参数
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            print(f"获取员工信息状态码：{emp_info_response.status_code}")
            
            if emp_info_response.status_code == 200:
                emp_info_data = emp_info_response.json()
                print(f"员工信息：{json.dumps(emp_info_data, ensure_ascii=False, indent=2)}")
            else:
                print(f"获取员工信息失败：{emp_info_response.text}")
                
        else:
            print(f"登录失败：{login_response.text}")
            
    except Exception as e:
        print(f"测试过程中出现错误：{str(e)}")

def debug_database():
    """调试数据库中的员工数据"""
    print("\n=== 数据库调试 ===")
    
    # 直接使用SQL查询检查数据
    import pymysql
    
    try:
        connection = pymysql.connect(
            host='127.0.0.1',
            user='root',
            password='root',
            database='esri_test'
        )
        
        with connection.cursor() as cursor:
            # 检查员工账号
            print("--- 员工账号表 ---")
            cursor.execute("SELECT * FROM employee_account WHERE employee_user_name = 'emp_test_2024'")
            account_result = cursor.fetchone()
            print(f"员工账号记录：{account_result}")
            
            # 检查员工信息表
            print("\n--- 员工信息表 ---")
            cursor.execute("SELECT * FROM employee_info WHERE employee_number = 'emp_test_2024'")
            info_result = cursor.fetchone()
            print(f"员工信息记录：{info_result}")
            
            # 检查所有员工信息
            print("\n--- 所有员工信息 ---")
            cursor.execute("SELECT employee_number, name, phone_number FROM employee_info")
            all_emp_info = cursor.fetchall()
            print(f"员工信息总数：{len(all_emp_info)}")
            for emp in all_emp_info:
                print(f"员工编号：{emp[0]}，姓名：{emp[1]}，电话：{emp[2] if len(emp) > 2 else '无'}")
                
            # 检查表结构
            print("\n--- 员工信息表结构 ---")
            cursor.execute("DESCRIBE employee_info")
            table_structure = cursor.fetchall()
            print("表结构：")
            for column in table_structure:
                print(f"  {column[0]}: {column[1]}")
                
    except Exception as e:
        print(f"数据库查询错误：{str(e)}")
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    test_personal_center()
    debug_database()
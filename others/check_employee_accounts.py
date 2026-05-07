#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查员工账户信息并测试个人中心
小白说明：这个脚本用来查看数据库中的员工账户，然后用正确的凭据测试个人中心
"""

import requests
import os
import sys
import importlib.util
from typing import cast

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'testrealend'))

from flask import Flask

def check_employee_accounts():
    """检查数据库中的员工账户"""
    print("🔍 检查数据库中的员工账户...")
    
    try:
        app_path = os.path.join(project_root, 'testrealend', 'app.py')
        spec = importlib.util.spec_from_file_location('testrealend_app', app_path)
        if spec is None or spec.loader is None:
            raise RuntimeError('无法加载 testrealend/app.py')
        app_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_module)
        app = cast(Flask, app_module.app)
        
        with app.app_context():
            from testrealend.model.models import EmployeeAccount, EmployeeInfo
            
            # 查询所有员工账户
            accounts = EmployeeAccount.query.all()
            print(f"📊 找到 {len(accounts)} 个员工账户:")
            
            for account in accounts:
                print(f"\n👤 账户信息:")
                print(f"  ID: {account.id}")
                print(f"  用户名: {account.employee_user_name}")
                print(f"  员工编号: {account.employee_number}")
                print(f"  创建时间: {account.create_time}")
                print(f"  状态: {account.status}")
                
                # 获取对应的员工信息
                employee_info = EmployeeInfo.query.filter_by(employee_number=account.employee_number).first()
                if employee_info:
                    print(f"  姓名: {employee_info.name}")
                    print(f"  电话: {employee_info.phone_number}")
                    print(f"  地址: {employee_info.address}")
                else:
                    print("  ⚠️ 没有找到对应的员工信息")
                    
            return accounts
            
    except Exception as e:
        print(f"❌ 数据库查询失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def test_login_with_correct_credentials(accounts):
    """使用正确的账户信息测试登录"""
    print(f"\n🔑 使用正确的账户信息测试登录...")
    
    if not accounts:
        print("❌ 没有可用的员工账户")
        return None, None
    
    # 使用第一个账户
    account = accounts[0]
    username = account.employee_user_name
    
    login_data = {
        'username': username,
        'password': '123456',  # 默认密码
        'role': 'employee'
    }
    
    print(f"尝试登录 - 用户名: {username}, 密码: 123456")
    
    try:
        response = requests.post(
            'http://localhost:5001/api/login',
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"登录状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 登录成功")
            return data.get('access_token'), data.get('refresh_token')
        else:
            print(f"❌ 登录失败: {response.text}")
            return None, None
            
    except Exception as e:
        print(f"❌ 登录异常: {str(e)}")
        return None, None

def test_personal_center_with_correct_auth(access_token, accounts):
    """使用正确的认证测试个人中心"""
    print(f"\n🧪 使用正确的认证测试个人中心...")
    
    if not access_token or not accounts:
        print("❌ 缺少认证令牌或账户信息")
        return
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            'http://localhost:5001/api/employee/profile',
            headers=headers
        )
        
        print(f"个人中心API状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 个人中心API正常工作")
            print("📋 员工资料:")
            
            profile = data.get('data', {})
            print(f"  员工编号: {profile.get('employee_number', 'N/A')}")
            print(f"  姓名: {profile.get('name', 'N/A')}")
            print(f"  工号: {profile.get('job_number', 'N/A')}")
            print(f"  电话: {profile.get('phone_number', 'N/A')}")
            print(f"  地址: {profile.get('address', 'N/A')}")
            print(f"  邮箱: {profile.get('email', 'N/A')}")
            print(f"  部门: {profile.get('department', 'N/A')}")
            print(f"  职位: {profile.get('position', 'N/A')}")
            
            if profile.get('avatar'):
                print("✅ 包含头像数据")
            else:
                print("⚠️ 没有头像数据")
                
        else:
            print(f"❌ 个人中心API失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 个人中心API测试异常: {str(e)}")

if __name__ == "__main__":
    print("🔍 员工账户检查和个人中心测试")
    print("=" * 60)
    
    # 1. 检查员工账户
    accounts = check_employee_accounts()
    
    if accounts:
        # 2. 使用正确的凭据登录
        access_token, refresh_token = test_login_with_correct_credentials(accounts)
        
        if access_token:
            # 3. 测试个人中心
            test_personal_center_with_correct_auth(access_token, accounts)
        else:
            print("\n❌ 无法获取认证令牌")
    else:
        print("\n❌ 数据库中没有员工账户")
    
    print("\n🔍 测试完成")

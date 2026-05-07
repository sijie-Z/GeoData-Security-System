#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
员工管理API详细调试脚本 - 修复版
小白说明：这个脚本专门用来解决 'NoneType' object has no attribute 'employee_number' 错误
"""

import requests
import json
import os
import sys

# 添加项目根目录到Python路径，这样才能正确导入模块
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_api_error():
    """测试API错误详情"""
    print("🧪 测试员工管理API错误...")
    
    try:
        # 直接访问API获取详细错误
        response = requests.get('http://localhost:5001/api/adm/get_emp_info_list')
        print(f"📊 状态码: {response.status_code}")
        
        if response.status_code == 500:
            error_data = response.json()
            print(f"❌ 服务器错误详情:")
            print(json.dumps(error_data, indent=2, ensure_ascii=False))
            
            # 获取错误消息
            error_msg = error_data.get('msg', '')
            if "'NoneType' object has no attribute 'employee_number'" in error_msg:
                print("\n🔍 错误分析:")
                print("这个错误说明员工列表中包含了None值")
                print("可能的原因：")
                print("1. 数据库查询返回了None值")
                print("2. 员工数据不完整")
                print("3. 数据库连接问题")
                
        elif response.status_code == 200:
            print("✅ API正常工作")
        else:
            print(f"❓ 意外状态码: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")

def test_database_connection():
    """测试数据库连接和员工数据"""
    print("\n🧪 测试数据库连接...")
    
    try:
        # 设置Flask应用环境
        os.environ['FLASK_APP'] = 'testrealend.app'
        from testrealend.app import app
        
        with app.app_context():
            from testrealend.model.models import EmployeeInfo
            
            print("✅ 数据库连接成功")
            
            # 查询所有员工
            employees = EmployeeInfo.query.all()
            print(f"📊 员工总数: {len(employees)}")
            
            if employees:
                print("\n📋 员工详情:")
                for i, emp in enumerate(employees):
                    print(f"员工 {i+1}:")
                    print(f"  ID: {emp.id}")
                    print(f"  员工编号: {emp.employee_number}")
                    print(f"  姓名: {emp.name}")
                    print(f"  工号: {emp.job_number}")
                    print(f"  电话: {emp.phone_number}")
                    print(f"  地址: {emp.address}")
                    print()
                    
                    # 检查是否有None值
                    if emp.employee_number is None:
                        print(f"  ⚠️ 警告：员工编号为None！")
                    if emp.name is None:
                        print(f"  ⚠️ 警告：员工姓名为None！")
            else:
                print("⚠️ 数据库中没有员工数据")
                
    except Exception as e:
        print(f"❌ 数据库测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

def test_adm_server_directly():
    """直接测试AdmServer"""
    print("\n🧪 直接测试AdmServer...")
    
    try:
        # 设置Flask应用环境
        os.environ['FLASK_APP'] = 'testrealend.app'
        from testrealend.app import app
        
        with app.app_context():
            from testrealend.server.adm_server import AdmServer
            
            server = AdmServer()
            emp_list, count = server.get_emp_info_list()
            
            print(f"📊 AdmServer返回结果:")
            print(f"员工列表类型: {type(emp_list)}")
            print(f"员工数量: {count}")
            
            if emp_list:
                print(f"第一个员工类型: {type(emp_list[0])}")
                
                # 检查是否有None值
                none_count = sum(1 for emp in emp_list if emp is None)
                if none_count > 0:
                    print(f"❌ 发现 {none_count} 个None值在员工列表中！")
                
                # 检查每个员工
                for i, emp in enumerate(emp_list):
                    if emp is None:
                        print(f"❌ 员工 {i} 是None值！")
                    else:
                        try:
                            emp_num = emp.employee_number
                            print(f"✅ 员工 {i}: {emp_num} - {emp.name}")
                        except AttributeError as e:
                            print(f"❌ 员工 {i} 属性错误: {str(e)}")
            else:
                print("⚠️ 员工列表为空")
                
    except Exception as e:
        print(f"❌ AdmServer测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

def check_adm_resource():
    """检查adm_resource.py中的错误处理"""
    print("\n🧪 检查adm_resource.py中的错误处理...")
    
    try:
        # 读取adm_resource.py文件，查看GetEmpInfoList类
        adm_resource_path = os.path.join(project_root, 'testrealend', 'resource', 'adm_resource.py')
        
        with open(adm_resource_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 查找GetEmpInfoList类
        if 'class GetEmpInfoList(Resource):' in content:
            print("✅ 找到GetEmpInfoList类")
            
            # 检查get方法
            get_method_start = content.find('def get(self):')
            if get_method_start != -1:
                # 提取get方法的内容（简化版）
                method_content = content[get_method_start:get_method_start + 1000]
                print("📋 get方法的前1000个字符:")
                print(method_content)
                
                # 检查是否有对None值的处理
                if 'emp_info.employee_number' in method_content:
                    print("\n🔍 发现问题：代码中直接访问了emp_info.employee_number")
                    print("如果emp_info是None，就会导致 'NoneType' object has no attribute 'employee_number' 错误")
                    
                    # 建议修复方案
                    print("\n💡 修复建议:")
                    print("在访问emp_info属性之前，先检查emp_info是否为None")
                    print("或者在查询数据库时过滤掉None值")
            else:
                print("❌ 没有找到get方法")
        else:
            print("❌ 没有找到GetEmpInfoList类")
            
    except Exception as e:
        print(f"❌ 文件检查失败: {str(e)}")

if __name__ == "__main__":
    print("🔍 员工管理错误详细调试开始")
    print("=" * 60)
    
    # 测试API错误
    test_api_error()
    
    # 测试数据库
    print("\n" + "=" * 60)
    test_database_connection()
    
    # 测试AdmServer
    print("\n" + "=" * 60)
    test_adm_server_directly()
    
    # 检查资源文件
    print("\n" + "=" * 60)
    check_adm_resource()
    
    print("\n🔍 调试完成")
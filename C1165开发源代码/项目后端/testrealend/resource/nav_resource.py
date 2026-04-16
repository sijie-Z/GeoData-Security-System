from flask_restful import Resource
from flask import request, jsonify
from server.nav_server import AdmNavServer, EmpNavServer


class AdmNavResource1(Resource):
    def get(self):
        try:
            adm_nav_data = AdmNavServer().get_nav_list()
            # print("Raw nav data:", adm_nav_data)
            adm_nav_tree = AdmNavServer().build_adm_nav_tree(adm_nav_data)
            # print("Processed nav tree:", adm_nav_tree)
            return jsonify({
                "data": adm_nav_tree,
                "msg": "记录获取成功",
                "status": True
            })
        except Exception as e:
            print(f"记录获取失败: {str(e)}")
            return {
                "msg": f"记录获取失败: {str(e)}",
                "status": False
            }, 500


class EmpNavResource1(Resource):
    def get(self):
        try:
            emp_nav_data = EmpNavServer().get_nav_list()
            emp_nav_tree = EmpNavServer().build_emp_nav_tree(emp_nav_data)
            return jsonify({
                "data": emp_nav_tree,
                "msg": "记录获取成功",
                "status": True
            })
        except Exception as e:
            print(f"记录获取失败: {str(e)}")  # 添加日志输出
            return {
                "msg": f"记录获取失败: {str(e)}",
                "status": False
            }, 500

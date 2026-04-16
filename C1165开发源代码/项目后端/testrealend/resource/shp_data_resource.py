from flask import request, jsonify
from flask_restful import Resource
from server.shp_data_server import ShpDataServer


class ShpDataByIdResource(Resource):
    def get(self):
        # 处理 URL 参数
        shp_data_id = request.args.get('id', type=int)

        if shp_data_id is None:
            return jsonify({
                "data": None,
                "msg": "ID 参数缺失",
                "status": False
            }), 400

        shp_data_server = ShpDataServer()
        shp_data = shp_data_server.get_shp_data_id(shp_data_id)

        if shp_data:
            data_scu = {
                'data': {
                    "data_id": shp_data.id,
                    'data_name': shp_data.name,
                    'data_alias': shp_data.alias,
                    'geomtype': shp_data.geomtype,
                    'introduction': shp_data.introduction,
                    'data_url': shp_data.url,
                    'datetime': shp_data.datetime,
                    'uuid': str(shp_data.uuid),
                    'layer': shp_data.layer
                },
                "msg": "记录获取成功",
                "status": True
            }
            return jsonify(data_scu), 200
        else:
            data_fail = {
                "data": None,
                "msg": "记录获取失败",
                "status": False
            }
            return jsonify(data_fail), 404



# shp_data_resource.py
from flask import request # jsonify不需要，因为Flask-RESTful会自动处理
from flask_restful import Resource
# from flask_jwt_extended import jwt_required, get_jwt_identity # 如果需要JWT保护
from server.shp_data_server import ShpDataServer # 确保路径正确
import traceback # 用于打印详细的异常信息

# ShpUploadResource 和 ShpDataByIdResource 保持你之前的定义，确保它们能正常工作。
# 这里主要关注 ShpDataListResource

class ShpDataListResource(Resource):
    # @jwt_required() # 如果需要保护
    def get(self):
        print("DEBUG (Resource): ShpDataListResource GET method entered.")
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 10)) # 与前端和server层默认值一致
            keyword = request.args.get('keyword', None)
            print(f"DEBUG (Resource): Received params: page={page}, pageSize={page_size}, keyword='{keyword}'")

            shp_data_server = ShpDataServer()
            # get_data_list 返回 (list_of_dictionaries, pagination_dictionary)
            # 或者在错误时返回 ([], error_pagination_dictionary_with_error_flag)
            list_of_dicts, pagination_info = shp_data_server.get_data_list(page, page_size, keyword)

            print(f"DEBUG (Resource): Received from service - list count: {len(list_of_dicts) if list_of_dicts is not None else 'None'}, pagination: {pagination_info}")

            # 检查服务层是否通过pagination_info明确返回了错误
            if pagination_info and pagination_info.get('error'):
                print(f"DEBUG (Resource): Error identified from service layer: {pagination_info.get('message')}")
                return {
                    'msg': pagination_info.get('message', '获取列表时发生内部错误'),
                    'status': False,
                    'data': {'list': [], 'pages': pagination_info} # 即使错误，也保持data结构
                }, 500 # 服务层错误通常是500

            # 如果列表是None（服务层内部发生未标记的严重错误），也视为错误
            if list_of_dicts is None:
                print("DEBUG (Resource): list_of_dicts_from_server is None, treating as an error.")
                return {
                     'msg': '服务层未能返回有效数据列表，发生未知错误。',
                     'status': False,
                     'data': {'list': [], 'pages': pagination_info or {}}
                }, 500

            # 到这里，list_of_dicts 应该是一个列表 (可能是空列表)
            # pagination_info 应该是一个包含分页信息的字典
            # ShpDataServer 中的 to_dict 已经处理了字段名，这里直接使用

            response_payload = {
                'data': {
                    'list': list_of_dicts,
                    'pages': pagination_info,
                    # 'rows': len(list_of_dicts) # 这个可以由前端 list.length 或 pages.total 得到
                },
                'msg': "记录获取成功",
                "status": True
            }
            # print(f"DEBUG (Resource): Returning from GET (success): {response_payload}")
            return response_payload, 200 # Flask-RESTful 会自动 jsonify
        except Exception as e:
            error_message = f"Critical unhandled exception in ShpDataListResource: {type(e).__name__} - {str(e)}"
            print(f"!!!!!!!!!!!!!!!!! CRITICAL ERROR in ShpDataListResource !!!!!!!!!!!!!!!!!")
            traceback.print_exc()
            print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            return {'msg': "服务器发生严重错误，请联系管理员", 'status': False, 'data': None}, 500

# ShpDataByIdResource 和 ShpUploadResource (如果存在) 应该保持不变或类似地增强错误处理
class ShpDataByIdResource(Resource):
    def get(self):
        # (保持你之前的实现，但可以增加类似的DEBUG打印和错误处理)
        shp_data_id = request.args.get('id', type=int)
        if shp_data_id is None:
            return {'data': None, 'msg': "ID 参数缺失", 'status': False}, 400

        shp_data_server = ShpDataServer()
        shp_data_obj = shp_data_server.get_shp_data_id(shp_data_id)

        if shp_data_obj:
            # 假设 shp_data_obj.to_dict() 返回前端期望的格式
            return {'data': shp_data_obj.to_dict(), 'msg': "记录获取成功", 'status': True}, 200
        else:
            return {'data': None, 'msg': "未找到指定ID的记录", 'status': False}, 404
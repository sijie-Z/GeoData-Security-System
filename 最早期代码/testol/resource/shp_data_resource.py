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
            })
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
                    'datetime': shp_data.datetime
                },
                "msg": "记录获取成功",
                "status": True
            }
            return jsonify(data_scu)
        else:
            data_fail = {
                "data": None,
                "msg": "记录获取失败",
                "status": False
            }
            return jsonify(data_fail)


class ShpDataListResource(Resource):
    def get(self):
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 3))
            keyword = request.args.get('keyword', None)
            shp_data_server = ShpDataServer()
            shp_datas, pagination = shp_data_server.get_data_list(page, page_size, keyword)
            data_list = []
            for shp_data in shp_datas:
                data_list.append({

                    'data_id': shp_data['id'],  # shp_data['id']不能使用 shp_data.id
                    'data_name': shp_data['name'],
                    'data_alias': shp_data['alias'],
                    'geomtype': shp_data['geomtype'],
                    'data_url': shp_data['url'],
                    'uuid': shp_data['uuid'],
                    # 'GetCapabilities': shp_data['GetCapabilities'],
                    'layer': shp_data['layer'],
                    'data_introduction': shp_data['introduction'],

                })

                print(shp_data['layer'])

            if not pagination:
                pagination = {
                    'has_next': False,
                    'has_previous': False,
                    'next': None,
                    'number': [],
                    'page': 1,
                    'page_size': page_size,
                    'pages': 1,
                    'previous': None,
                    'total': 0
                }
            response = {
                'data': {
                    'list': data_list,
                    'pages': pagination,
                    'rows': len(data_list)  # 把shp_data改成data_list
                },
                'msg': "记录获取成功",
                "status": True
            }
            return response, 200
        except Exception as e:
            response = {
                'msg': f'记录获取失败: {str(e)}',
                'status': False
            }
            return response, 500

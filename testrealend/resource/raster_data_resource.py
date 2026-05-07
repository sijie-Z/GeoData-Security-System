from flask import request, jsonify
from flask_restful import Resource
import traceback
import logging
from server.raster_data_server import RasterDataServer

class RasterDataByIdResource(Resource):
    def get(self):
        try:
            data_id = request.args.get('id', type=int)
            if not data_id:
                return jsonify({
                    "data": None,
                    "msg": "ID 参数缺失",
                    "status": False
                }), 400

            raster_data_server = RasterDataServer()
            raster_data = raster_data_server.get_by_id(data_id)

            if raster_data:
                return jsonify({
                    "data": {
                        'data_id': raster_data.id,
                        'data_alias': raster_data.alias,
                        'uuid': str(raster_data.uuid) if raster_data.uuid else None,
                        'coordinate_system': raster_data.coordinate_system,
                        'data_source': raster_data.data_source,
                        'geomtype': '栅格',
                        'data_url': raster_data.url,
                        'resolution': raster_data.resolution if hasattr(raster_data, 'resolution') else None,
                        'band_count': raster_data.band_count,
                        'file_path': raster_data.raster_file_path
                    },
                    "msg": "记录获取成功",
                    "status": True
                }), 200
            else:
                return jsonify({
                    "data": None,
                    "msg": "记录获取失败",
                    "status": False
                }), 404
        except Exception as e:
            traceback.print_exc()
            logging.error(str(e))
            return jsonify({
                "data": None,
                "msg": "操作失败，请稍后重试",
                "status": False
            }), 500

class RasterDataListResource(Resource):
    def get(self):
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 10))
            keyword = request.args.get('keyword', None)

            raster_data_server = RasterDataServer()
            list_of_dicts, pagination_info = raster_data_server.get_data_list(page, page_size, keyword)

            if list_of_dicts is None:
                return jsonify({
                    'msg': '服务层未能返回有效数据列表，发生未知错误。',
                    'status': False,
                    'data': {'list': [], 'pages': pagination_info or {}}
                }), 500

            response_payload = {
                'data': {
                    'list': list_of_dicts,
                    'pages': pagination_info,
                },
                'msg': "记录获取成功",
                "status": True
            }
            return jsonify(response_payload), 200
        except Exception as e:
            traceback.print_exc()
            logging.error(str(e))
            return jsonify({
                'msg': "操作失败，请稍后重试",
                'status': False,
                'data': None
            }), 500
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required
from model.Shp_Data import Shp
from model.Raster_Data import RasterData
from extension.extension import db

class VectorDataViewingResource(Resource):
    @jwt_required()
    def get(self):
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 12, type=int)
        keyword = request.args.get('keyword', '')

        query = Shp.query
        if keyword:
            # Escape special LIKE characters to prevent injection
            safe_keyword = keyword.replace('%', r'\%').replace('_', r'\_')
            query = query.filter(Shp.alias.like(f'%{safe_keyword}%', escape='\\'))
        
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        items = [item.to_dict() for item in pagination.items]
        
        return {
            'status': True,
            'data': {
                'list': items,
                'pages': {
                    'total': pagination.total,
                    'pages': pagination.pages
                }
            }
        }, 200

class RasterDataViewingResource(Resource):
    @jwt_required()
    def get(self):
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 12, type=int)
        keyword = request.args.get('keyword', '')

        query = RasterData.query
        if keyword:
            # Escape special LIKE characters to prevent injection
            safe_keyword = keyword.replace('%', r'\%').replace('_', r'\_')
            query = query.filter(RasterData.alias.like(f'%{safe_keyword}%', escape='\\'))
        
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        items = [item.to_dict() for item in pagination.items]
        
        return {
            'status': True,
            'data': {
                'list': items,
                'pages': {
                    'total': pagination.total,
                    'pages': pagination.pages
                }
            }
        }, 200

class ShpDataListResource(Resource):
    @jwt_required()
    def get(self):
        # Legacy or generic data viewing
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        
        pagination = Shp.query.paginate(page=page, per_page=page_size, error_out=False)
        return {
            'status': True,
            'data': [item.to_dict() for item in pagination.items],
            'total': pagination.total
        }, 200

class ShpDataByIdResource(Resource):
    @jwt_required()
    def get(self):
        data_id = request.args.get('id', type=int)
        item = Shp.query.get(data_id)
        if item:
            return {'status': True, 'data': item.to_dict()}, 200
        return {'status': False, 'msg': '数据不存在'}, 404

class MapSearchResource(Resource):
    @jwt_required()
    def get(self):
        keyword = request.args.get('keyword', '')
        if not keyword:
            return {'status': False, 'msg': '请输入关键词'}, 400

        # Search from Shp and RasterData by keyword match on alias
        shp_results = Shp.query.filter(Shp.alias.contains(keyword)).limit(5).all()
        raster_results = RasterData.query.filter(RasterData.alias.contains(keyword)).limit(5).all()

        pois = []
        for s in shp_results:
            pois.append({'name': s.alias, 'type': 'vector', 'id': s.id})
        for r in raster_results:
            pois.append({'name': r.alias, 'type': 'raster', 'id': r.id})

        return {'status': True, 'pois': pois}, 200

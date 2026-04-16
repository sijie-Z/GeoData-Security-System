from model.Raster_Data import RasterData  # 使用正确的文件名
from extension.extension import db
from sqlalchemy import or_
import traceback

class RasterDataServer:
    def get_data_list(self, page, page_size, keyword=None):
        try:
            query = RasterData.query
            
            if keyword:
                query = query.filter(
                    or_(
                        RasterData.name.ilike(f'%{keyword}%'),
                        RasterData.alias.ilike(f'%{keyword}%'),
                        RasterData.uuid.ilike(f'%{keyword}%')
                    )
                )
            
            paginated_data = query.paginate(page=page, per_page=page_size, error_out=False)
            
            raster_list = []
            for item in paginated_data.items:
                raster_list.append({
                    'data_id': item.id,
                    'data_alias': item.alias,
                    'uuid': str(item.uuid) if item.uuid else None,
                    'coordinate_system': item.coordinate_system,
                    'data_source': item.data_source,
                    'geomtype': '栅格',
                    'data_url': item.url,
                    'resolution': item.resolution,
                    'band_count': item.bands
                })
            
            pagination_info = {
                'page': page,
                'pageSize': page_size,
                'total': paginated_data.total,
                'pages': paginated_data.pages
            }
            
            return raster_list, pagination_info
        except Exception as e:
            traceback.print_exc()
            return None, {
                'error': True,
                'message': f"服务层错误: {str(e)}",
                'page': page,
                'pageSize': page_size,
                'total': 0,
                'pages': 0
            }

    def get_by_id(self, data_id):
        try:
            return RasterData.query.get(data_id)
        except Exception as e:
            traceback.print_exc()
            return None
# # from model.Shp_File import ShpFile
# from model.Shp_Data import Shp
# from extension.extension import db
# from sqlalchemy import or_, cast
# from sqlalchemy.types import String


# class ShpDataServer:
#     def get_data_list(self, page, page_size, keyword=None):
#         try:
#             query = db.session.query(Shp)

#             if keyword:
#                 keyword_filter = f"%{keyword}%"
#                 if keyword.isdigit():
#                     query = query.filter(
#                         or_(
#                             cast(Shp.id, String).ilike(keyword_filter),
#                             Shp.name.ilike(keyword_filter),
#                             Shp.alias.ilike(keyword_filter),
#                             Shp.geomtype.ilike(keyword_filter)
#                         )
#                     )
#                 else:
#                     query = query.filter(
#                         or_(
#                             Shp.name.ilike(keyword_filter),
#                             Shp.alias.ilike(keyword_filter),
#                             Shp.geomtype.ilike(keyword_filter)
#                         )
#                     )

#             total_data = query.count()
#             shp_datas = query.offset((page - 1) * page_size).limit(page_size).all()

#             total_pages = (total_data + page_size - 1) // page_size
#             has_previous = page > 1
#             has_next = page < total_pages
#             previous_page = page - 1 if has_previous else 0
#             next_page = page + 1 if has_next else 0

#             pagination = {
#                 'page': page,
#                 'page_size': page_size,
#                 'pages': total_pages,
#                 'total': total_data,
#                 'has_previous': has_previous,
#                 'has_next': has_next,
#                 'previous': previous_page,
#                 'next': next_page,
#                 'number': list(range(1, total_pages + 1))
#             }
#             return [shp_data.to_dict() for shp_data in shp_datas], pagination

#         except Exception as e:
#             print(e)
#             return [], {}

#     def get_shp_data_id(self, shp_id: int):
#         shp_data = db.session.query(Shp).filter_by(id=shp_id).first()
#         return shp_data



# shp_data_server.py
from sqlalchemy import or_, cast, func
from sqlalchemy.types import String
from model.Shp_Data import Shp
from extension.extension import db
import traceback # 用于打印详细的异常信息

class ShpDataServer:
    def get_data_list(self, page: int, page_size: int, keyword: str = None):
        print(f"DEBUG (ShpDataServer): get_data_list called - page={page}, pageSize={page_size}, keyword='{keyword}'")
        try:
            query = db.session.query(Shp)

            if keyword:
                keyword_filter = f"%{keyword}%"
                search_conditions = [
                    Shp.name.ilike(keyword_filter),
                    Shp.alias.ilike(keyword_filter),
                    Shp.geomtype.ilike(keyword_filter)
                ]
                if keyword.isdigit():
                    search_conditions.append(cast(Shp.id, String).ilike(keyword_filter))
                query = query.filter(or_(*search_conditions))

            # 先获取总数
            total_data_query = query.order_by(None) # 移除 order_by 避免影响 count
            total_data = total_data_query.count()
            print(f"DEBUG (ShpDataServer): Total data matching keyword: {total_data}")

            if page_size <= 0: # 防御 page_size 为0或负数
                page_size = 10 # 或者你希望的默认值

            total_pages = 0
            if total_data > 0:
                total_pages = (total_data + page_size - 1) // page_size
            
            # 确保页码在有效范围内
            if page < 1:
                page = 1
            if total_pages > 0 and page > total_pages: # 只有在有内容时才限制最大页
                page = total_pages
            elif total_pages == 0: # 如果没有数据或没有页数，则当前页应为1（或0）
                page = 1


            shp_datas_query_result = []
            if total_data > 0: # 只有当有数据时才进行分页查询
                # 确保 (page - 1) * page_size 不会是负数
                offset_val = (page - 1) * page_size
                if offset_val < 0: offset_val = 0 # 虽然上面的page修正应该避免了，但多一层保险

                shp_datas_query_result = query.order_by(Shp.id.asc()).offset(offset_val).limit(page_size).all()
            
            print(f"DEBUG (ShpDataServer): Fetched {len(shp_datas_query_result)} records for page {page}")

            has_previous = page > 1
            has_next = page < total_pages if total_pages > 0 else False # 只有在有总页数时才判断下一页

            pagination = {
                'page': page,
                'page_size': page_size,
                'pages': total_pages,
                'total': total_data,
                'has_previous': has_previous,
                'has_next': has_next,
                'previous': page - 1 if has_previous else None,
                'next': page + 1 if has_next else None,
                # 'number': list(range(1, total_pages + 1)) # 这个通常不需要后端返回
            }
            
            # 调用模型中的 to_dict() 方法
            list_of_dicts = [shp_data_item.to_dict() for shp_data_item in shp_datas_query_result]
            
            print(f"DEBUG (ShpDataServer): Returning from get_data_list (success). List count: {len(list_of_dicts)}. Pagination: {pagination}")
            return list_of_dicts, pagination

        except Exception as e:
            error_message = f"Error in ShpDataServer.get_data_list: {type(e).__name__} - {str(e)}"
            print(f"!!!!!!!!!!!!!!!!! DATABASE ERROR in ShpDataServer.get_data_list !!!!!!!!!!!!!!!!!")
            traceback.print_exc()
            print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            db.session.rollback()
            
            # 返回一个清晰的错误指示，同时保持分页结构
            error_pagination = {
                'error': True,
                'message': error_message,
                'page': page if 'page' in locals() else 1,
                'page_size': page_size if 'page_size' in locals() else 10,
                'pages': 0, 'total': 0,
                'has_previous': False, 'has_next': False,
                'previous': None, 'next': None
            }
            print(f"DEBUG (ShpDataServer): Returning from get_data_list (exception). Pagination: {error_pagination}")
            return [], error_pagination # 返回空列表和错误分页对象

    def get_shp_data_id(self, shp_id: int):
        # (保持你之前的 get_shp_data_id 实现，确保它返回模型对象或None)
        print(f"DEBUG (ShpDataServer): get_shp_data_id called with shp_id={shp_id}")
        try:
            shp_data = db.session.query(Shp).filter_by(id=shp_id).first()
            return shp_data
        except Exception as e:
            error_message = f"Error in ShpDataServer.get_shp_data_id for id={shp_id}: {type(e).__name__} - {str(e)}"
            print(f"--- DATABASE ERROR in ShpDataServer.get_shp_data_id: {error_message} ---")
            traceback.print_exc()
            db.session.rollback()
            return None
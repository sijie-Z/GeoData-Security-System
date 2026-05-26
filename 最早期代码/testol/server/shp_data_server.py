from model.Shp_Data import Shp
from extension.extension import db
from sqlalchemy import or_, cast
from sqlalchemy.types import String


class ShpDataServer:
    def get_data_list(self, page, page_size, keyword=None):
        try:
            query = db.session.query(Shp)
            if keyword:
                keyword_filter = f"%{keyword}%"
                if keyword.isdigit():
                    query = query.filter(
                        or_(
                            cast(Shp.id, String).ilike(keyword_filter),
                            Shp.name.ilike(keyword_filter),
                            Shp.alias.ilike(keyword_filter),
                            Shp.geomtype.ilike(keyword_filter),
                            Shp.uuid.ilike(keyword_filter)
                        )
                    )
                else:
                    query = query.filter(
                        or_(
                            Shp.name.ilike(keyword_filter),
                            Shp.alias.ilike(keyword_filter),
                            Shp.geomtype.ilike(keyword_filter),
                            Shp.uuid.ilike(keyword_filter)
                        )
                    )

            total_data = query.count()
            shp_datas = query.offset((page - 1) * page_size).limit(page_size).all()
            total_pages = (total_data + page_size - 1) // page_size
            has_previous = page > 1
            has_next = page < total_pages
            previous_page = page - 1 if has_previous else 0
            next_page = page + 1 if has_next else 0

            pagination = {
                'page': page,
                'page_size': page_size,
                'pages': total_pages,
                'total': total_data,
                'has_previous': has_previous,
                'has_next': has_next,
                'previous': previous_page,
                'next': next_page,
                'number': list(range(1, total_pages + 1))
            }
            return [shp_data.to_dict() for shp_data in shp_datas], pagination

        except Exception as e:
            print(e)
            return [], {}

    def get_shp_data_id(self, shp_id: int):
        shp_data = db.session.query(Shp).filter_by(id=shp_id).first()
        return shp_data

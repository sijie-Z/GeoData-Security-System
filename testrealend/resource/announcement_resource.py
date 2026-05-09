from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required
from model.Announcement import Announcement
from extension.extension import db
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from utils.required import admin_required
import logging


def _ensure_announcement_table():
    engine = db.session.get_bind(mapper=Announcement)
    Announcement.__table__.create(bind=engine, checkfirst=True)

class AnnouncementResource(Resource):
    @jwt_required()
    def get(self):
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        try:
            _ensure_announcement_table()
            query = Announcement.query.order_by(Announcement.created_at.desc())
            pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(str(e))
            return {
                'status': True,
                'data': {
                    'list': [],
                    'total': 0,
                    'pages': {
                        'page': page,
                        'pageSize': page_size,
                        'total': 0,
                        'pages': 0
                    }
                }
            }, 200
        
        items = [{
            'id': item.id,
            'title': item.title,
            'content': item.content,
            'tag': item.tag,
            'tag_color': item.tag_color,
            'icon': item.icon,
            'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for item in pagination.items]
        
        return {
            'status': True,
            'data': {
                'list': items,
                'total': pagination.total,
                'pages': {
                    'page': page,
                    'pageSize': page_size,
                    'total': pagination.total,
                    'pages': pagination.pages
                }
            }
        }, 200

    @admin_required
    def post(self):
        data = request.get_json()
        try:
            _ensure_announcement_table()
            new_ann = Announcement(
                title=data.get('title'),
                content=data.get('content'),
                tag=data.get('tag', '重要'),
                tag_color=data.get('tag_color', '#F59E0B'),
                icon=data.get('icon', 'InfoFilled'),
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(new_ann)
            db.session.commit()
            return {'status': True, 'msg': '公告发布成功'}, 201
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '公告服务不可用，请检查数据库配置'}, 500

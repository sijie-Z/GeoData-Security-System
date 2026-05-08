from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required
from model.Log_Info import LogInfo
from extension.extension import db
from utils.required import admin_required

class SystemLogResource(Resource):
    """
    System Operation Logs
    ---
    tags: [Logs]
    security: [Bearer: []]
    parameters:
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: pageSize
        type: integer
        default: 10
      - in: query
        name: username
        type: string
        description: Filter by username (partial match)
      - in: query
        name: user_number
        type: string
        description: Filter by user number
      - in: query
        name: action
        type: string
        description: Filter by action type
    responses:
      200: {description: Operation logs list}
    """
    @admin_required
    def get(self):
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        username = request.args.get('username')
        user_number = request.args.get('user_number')
        action = request.args.get('action')

        query = LogInfo.query
        if username:
            # Escape special LIKE characters to prevent injection
            safe_username = username.replace('%', r'\%').replace('_', r'\_')
            query = query.filter(LogInfo.username.like(f'%{safe_username}%', escape='\\'))
        if user_number:
            query = query.filter_by(user_number=user_number)
        if action:
            query = query.filter_by(action=action)

        pagination = query.order_by(LogInfo.timestamp.desc()).paginate(page=page, per_page=page_size, error_out=False)

        items = [{
            'timestamp': item.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'user_number': item.user_number,
            'username': item.username,
            'ip_address': item.ip_address,
            'action': item.action,
            'status': item.status,
            'details': item.details
        } for item in pagination.items]

        return {
            'status': True,
            'data': {
                'list': items,
                'total': pagination.total
            }
        }, 200

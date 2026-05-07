from io import BytesIO
import csv
import logging
from flask import request, send_file
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError
from extension.extension import db, limiter
from model.Employee_Info import EmployeeInfo
from model.Adm_Info import AdmInfo
from model.Log_Info import LogInfo
from model.Announcement import Announcement
from model.ChatMessage import ChatMessage
from model.FriendRequest import FriendRequest
from model.EmployeeNotification import EmployeeNotification


def _get_identity():
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if isinstance(identity, dict):
            return identity
    except Exception as e:
        logging.error(str(e))
        return {}
    return {}


def _me():
    identity = _get_identity()
    number = identity.get('number') or request.args.get('userNumber') or request.args.get('user_number')
    role = identity.get('role') or request.args.get('role') or 'employee'
    username = identity.get('username')
    return str(number) if number else None, str(role), username


def _display_name(number, role):
    if role == 'admin':
        adm = AdmInfo.query.filter_by(adm_number=str(number)).first()
        return adm.name if adm and adm.name else str(number)
    emp = EmployeeInfo.query.filter_by(employee_number=str(number)).first()
    return emp.name if emp and emp.name else str(number)


def _ensure_announcement_table():
    engine = db.session.get_bind(mapper=Announcement)
    Announcement.__table__.create(bind=engine, checkfirst=True)


class ProtectedResource(Resource):
    @jwt_required()
    def get(self):
        number, role, username = _me()
        return {'status': True, 'data': {'user_number': number, 'role': role, 'username': username}}, 200


class AdminEmployeeInfoResource(Resource):
    @jwt_required()
    def get(self):
        query = EmployeeInfo.query
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 1000, type=int)
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        items = [{
            'employee_number': i.employee_number,
            'name': i.name,
            'job_number': i.job_number,
            'phone_number': i.phone_number,
            'address': i.address
        } for i in pagination.items]
        return {'status': True, 'data': {'list': items, 'rows': pagination.total}}, 200


class AdminSendNotificationResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        content = (data.get('content') or '').strip()
        user_numbers = data.get('user_numbers') or []
        if not title or not content:
            return {'status': False, 'msg': '标题和内容不能为空'}, 400

        sender_number, _, sender_name = _me()
        if not user_numbers:
            recipients = [i.employee_number for i in EmployeeInfo.query.all()]
        else:
            recipients = [str(i) for i in user_numbers if str(i).strip()]

        records = [EmployeeNotification(
            user_number=n,
            title=title,
            content=content,
            sender_number=sender_number,
            sender_name=sender_name
        ) for n in recipients]
        if records:
            db.session.add_all(records)
            db.session.commit()
        return {'status': True, 'msg': f'发送成功，共 {len(records)} 条'}, 200


class EmployeeNotificationsResource(Resource):
    @jwt_required()
    def get(self):
        user_number, _, _ = _me()
        if not user_number:
            return {'status': False, 'msg': '未识别用户'}, 401
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        unread_only_raw = str(request.args.get('unread_only', 'false')).lower()
        unread_only = unread_only_raw in ['1', 'true', 'yes']

        query = EmployeeNotification.query.filter_by(user_number=user_number)
        if unread_only:
            query = query.filter_by(read=False)
        pagination = query.order_by(EmployeeNotification.created_at.desc()).paginate(page=page, per_page=page_size, error_out=False)
        items = [i.to_dict() for i in pagination.items]
        return {'status': True, 'data': {'list': items, 'total': pagination.total}}, 200


class EmployeeNotificationReadResource(Resource):
    @jwt_required()
    def post(self, notification_id):
        user_number, _, _ = _me()
        item = EmployeeNotification.query.filter_by(id=notification_id, user_number=user_number).first()
        if not item:
            return {'status': False, 'msg': '通知不存在'}, 404
        item.read = True
        db.session.commit()
        return {'status': True, 'msg': '已读'}, 200


class EmployeeMyLogsResource(Resource):
    @jwt_required()
    def get(self):
        user_number, _, _ = _me()
        if not user_number:
            user_number = request.args.get('userNumber')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        action = request.args.get('action')
        query = LogInfo.query.filter_by(user_number=user_number)
        if action:
            query = query.filter_by(action=action)
        pagination = query.order_by(LogInfo.timestamp.desc()).paginate(page=page, per_page=page_size, error_out=False)
        items = [i.to_dict() for i in pagination.items]
        return {'status': True, 'data': {'list': items, 'total': pagination.total}}, 200


class AdminAnnouncementManageResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        content = (data.get('content') or '').strip()
        if not title or not content:
            return {'status': False, 'msg': '标题和内容不能为空'}, 400
        try:
            _ensure_announcement_table()
            item = Announcement(
                title=title,
                content=content,
                author_id=(data.get('author_id') or '')
            )
            if hasattr(item, 'tag'):
                item.tag = data.get('tag')
            if hasattr(item, 'tag_color'):
                item.tag_color = data.get('tag_color')
            if hasattr(item, 'icon'):
                item.icon = data.get('icon')
            db.session.add(item)
            db.session.commit()
            return {'status': True, 'msg': '发布成功'}, 200
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '公告服务不可用，请检查数据库配置'}, 500

    def put(self):
        data = request.get_json() or {}
        item_id = data.get('id')
        try:
            _ensure_announcement_table()
            item = Announcement.query.get(item_id)
        except SQLAlchemyError as e:
            logging.error(str(e))
            return {'status': False, 'msg': '公告服务不可用，请检查数据库配置'}, 500
        if not item:
            return {'status': False, 'msg': '公告不存在'}, 404
        item.title = (data.get('title') or item.title).strip()
        item.content = (data.get('content') or item.content).strip()
        if hasattr(item, 'tag'):
            item.tag = data.get('tag', getattr(item, 'tag', None))
        if hasattr(item, 'tag_color'):
            item.tag_color = data.get('tag_color', getattr(item, 'tag_color', None))
        if hasattr(item, 'icon'):
            item.icon = data.get('icon', getattr(item, 'icon', None))
        try:
            db.session.commit()
            return {'status': True, 'msg': '更新成功'}, 200
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '更新失败，请检查数据库配置'}, 500

    def delete(self):
        item_id = request.args.get('id', type=int)
        try:
            _ensure_announcement_table()
            item = Announcement.query.get(item_id)
        except SQLAlchemyError as e:
            logging.error(str(e))
            return {'status': False, 'msg': '公告服务不可用，请检查数据库配置'}, 500
        if not item:
            return {'status': False, 'msg': '公告不存在'}, 404
        try:
            db.session.delete(item)
            db.session.commit()
            return {'status': True, 'msg': '删除成功'}, 200
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '删除失败，请检查数据库配置'}, 500


class ChatConversationsResource(Resource):
    @jwt_required()
    def get(self):
        me_number, me_role, _ = _me()
        if not me_number:
            return {'status': True, 'data': []}, 200
        rows = ChatMessage.query.filter(
            or_(
                and_(ChatMessage.sender_number == me_number, ChatMessage.sender_role == me_role),
                and_(ChatMessage.receiver_number == me_number, ChatMessage.receiver_role == me_role)
            )
        ).order_by(ChatMessage.created_at.desc()).all()
        seen = {}
        for m in rows:
            if m.sender_number == me_number and m.sender_role == me_role:
                peer_number = m.receiver_number
                peer_role = m.receiver_role
            else:
                peer_number = m.sender_number
                peer_role = m.sender_role
            key = f'{peer_role}:{peer_number}'
            if key in seen:
                continue
            unread_count = ChatMessage.query.filter_by(
                sender_number=peer_number,
                sender_role=peer_role,
                receiver_number=me_number,
                receiver_role=me_role,
                read=False
            ).count()
            seen[key] = {
                'peer_number': peer_number,
                'peer_role': peer_role,
                'peer_name': _display_name(peer_number, peer_role),
                'last_message': m.content,
                'last_time': m.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'unread_count': unread_count
            }
        return {'status': True, 'data': list(seen.values())}, 200


class ChatMessagesResource(Resource):
    @jwt_required()
    def get(self):
        me_number, me_role, _ = _me()
        peer_number = request.args.get('peer_number')
        peer_role = request.args.get('peer_role', 'employee')
        limit = request.args.get('limit', 150, type=int)
        if not me_number or not peer_number:
            return {'status': True, 'data': []}, 200
        rows = ChatMessage.query.filter(
            or_(
                and_(
                    ChatMessage.sender_number == me_number,
                    ChatMessage.sender_role == me_role,
                    ChatMessage.receiver_number == peer_number,
                    ChatMessage.receiver_role == peer_role
                ),
                and_(
                    ChatMessage.sender_number == peer_number,
                    ChatMessage.sender_role == peer_role,
                    ChatMessage.receiver_number == me_number,
                    ChatMessage.receiver_role == me_role
                )
            )
        ).order_by(ChatMessage.created_at.desc()).limit(max(1, min(500, limit))).all()
        rows = list(reversed(rows))
        items = [{
            'id': m.id,
            'content': m.content,
            'created_at': m.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_me': m.sender_number == me_number and m.sender_role == me_role
        } for m in rows]
        return {'status': True, 'data': items}, 200


class ChatMarkReadResource(Resource):
    @jwt_required()
    def post(self):
        me_number, me_role, _ = _me()
        data = request.get_json() or {}
        peer_number = data.get('peer_number')
        peer_role = data.get('peer_role', 'employee')
        if not me_number or not peer_number:
            return {'status': False, 'msg': '参数不完整'}, 400
        ChatMessage.query.filter_by(
            sender_number=str(peer_number),
            sender_role=str(peer_role),
            receiver_number=me_number,
            receiver_role=me_role,
            read=False
        ).update({'read': True})
        db.session.commit()
        return {'status': True, 'msg': '已读更新成功'}, 200


class ChatSearchUsersResource(Resource):
    @jwt_required()
    def get(self):
        me_number, me_role, _ = _me()
        keyword = (request.args.get('keyword') or '').strip()

        # 获取所有员工
        if keyword:
            safe_keyword = keyword.replace('%', r'\%').replace('_', r'\_')
            pattern = f'%{safe_keyword}%'
            emps = EmployeeInfo.query.filter(
                or_(
                    EmployeeInfo.employee_number.like(pattern, escape='\\'),
                    EmployeeInfo.name.like(pattern, escape='\\')
                )
            ).limit(30).all()
        else:
            emps = EmployeeInfo.query.limit(30).all()

        # 获取所有管理员
        adms = AdmInfo.query.limit(20).all()

        data = [{
            'number': i.employee_number,
            'name': i.name,
            'role': 'employee'
        } for i in emps if i.employee_number != me_number] + [{
            'number': i.adm_number,
            'name': i.name,
            'role': 'admin'
        } for i in adms if i.adm_number != me_number]

        return {'status': True, 'data': data}, 200


class ChatAddFriendResource(Resource):
    @jwt_required()
    def post(self):
        me_number, me_role, _ = _me()
        data = request.get_json() or {}
        friend_number = str(data.get('friend_number') or '')
        friend_role = str(data.get('friend_role') or 'employee')
        if not me_number or not friend_number:
            return {'status': False, 'msg': '参数不完整'}, 400
        if me_number == friend_number and me_role == friend_role:
            return {'status': False, 'msg': '不能添加自己'}, 400
        exists = FriendRequest.query.filter_by(
            owner_number=me_number,
            owner_role=me_role,
            friend_number=friend_number,
            friend_role=friend_role,
            status='pending'
        ).first()
        if exists:
            return {'status': True, 'msg': '申请已发送'}, 200
        req = FriendRequest(
            owner_number=me_number,
            owner_role=me_role,
            owner_name=_display_name(me_number, me_role),
            friend_number=friend_number,
            friend_role=friend_role,
            status='pending'
        )
        db.session.add(req)
        db.session.commit()
        return {'status': True, 'msg': '申请已发送'}, 200


class ChatFriendRequestsResource(Resource):
    @jwt_required()
    def get(self):
        me_number, me_role, _ = _me()
        rows = FriendRequest.query.filter_by(
            friend_number=me_number,
            friend_role=me_role,
            status='pending'
        ).order_by(FriendRequest.created_at.desc()).all()
        data = [{
            'id': i.id,
            'owner_number': i.owner_number,
            'owner_role': i.owner_role,
            'owner_name': i.owner_name,
            'created_at': i.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for i in rows]
        return {'status': True, 'data': data}, 200


class ChatFriendRespondResource(Resource):
    @jwt_required()
    def post(self):
        me_number, me_role, _ = _me()
        data = request.get_json() or {}
        request_id = data.get('request_id')
        action = str(data.get('action') or '').lower()
        req = FriendRequest.query.filter_by(
            id=request_id,
            friend_number=me_number,
            friend_role=me_role,
            status='pending'
        ).first()
        if not req:
            return {'status': False, 'msg': '申请不存在'}, 404
        req.status = 'accepted' if action == 'accept' else 'rejected'
        db.session.commit()
        return {'status': True, 'msg': '操作成功'}, 200


class ChatSendResource(Resource):
    @jwt_required()
    @limiter.limit("30 per minute")
    def post(self):
        me_number, me_role, _ = _me()
        data = request.get_json() or {}
        receiver_number = str(data.get('receiver_number') or '')
        receiver_role = str(data.get('receiver_role') or 'employee')
        content = (data.get('content') or '').strip()
        if not me_number or not receiver_number or not content:
            return {'status': False, 'msg': '参数不完整'}, 400
        msg = ChatMessage(
            sender_number=me_number,
            sender_role=me_role,
            receiver_number=receiver_number,
            receiver_role=receiver_role,
            content=content
        )
        db.session.add(msg)
        db.session.commit()
        return {'status': True, 'msg': '发送成功'}, 200


class BatchReviewFailedExportResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        failed = data.get('failed') or []
        output = BytesIO()
        text_buffer = output
        rows = []
        for item in failed:
            rows.append({
                'id': item.get('id', ''),
                'reason': item.get('reason', ''),
                'msg': item.get('msg', '')
            })
        csv_str = 'id,reason,msg\n'
        for r in rows:
            csv_str += f"{r['id']},{str(r['reason']).replace(',', '，')},{str(r['msg']).replace(',', '，')}\n"
        text_buffer.write(csv_str.encode('utf-8-sig'))
        text_buffer.seek(0)
        return send_file(
            text_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name='batch_review_failed.csv'
        )


class AdminUserListResource(Resource):
    @jwt_required()
    def get(self):
        identity = get_jwt_identity()
        if identity.get('role') != 'admin':
            return {'status': False, 'msg': '无权限'}, 403

        # 获取所有员工
        employees = EmployeeInfo.query.all()
        # 获取所有管理员
        admins = AdmInfo.query.all()

        emp_list = [{
            'employee_number': e.employee_number,
            'name': e.name,
            'role': 'employee'
        } for e in employees]

        adm_list = [{
            'adm_number': a.adm_number,
            'name': a.name,
            'role': 'admin'
        } for a in admins]

        return {
            'status': True,
            'data': {
                'employees': emp_list,
                'admins': adm_list
            }
        }, 200

"""WebSocket (Socket.IO) for real-time notifications with JWT authentication."""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_socketio = None


def init_socketio(app):
    """Initialize Flask-SocketIO with the app."""
    global _socketio
    try:
        from flask_socketio import SocketIO, emit, join_room, leave_room
        cors_origins = app.config.get('CORS_ORIGINS', ['http://localhost:5173'])
        _socketio = SocketIO(
            app,
            cors_allowed_origins=cors_origins,
            async_mode='threading',
            logger=False,
            engineio_logger=False
        )
        _register_handlers(_socketio, app)
        logger.info("Socket.IO initialized")
    except ImportError:
        logger.warning("flask-socketio not installed, WebSocket disabled")
    return _socketio


def get_socketio():
    return _socketio


def _verify_jwt_token(token, app):
    """Verify a JWT token and return the identity dict or None."""
    try:
        from flask_jwt_extended import decode_token
        with app.app_context():
            decoded = decode_token(token)
            return decoded.get('sub')
    except Exception as e:
        logger.debug(f"JWT verification failed: {e}")
        return None


def _register_handlers(sio, app):
    """Register Socket.IO event handlers with JWT authentication."""
    from flask_socketio import emit, join_room, leave_room
    from flask import request as flask_request

    authenticated_users = {}  # sid -> identity

    @sio.on('connect')
    def handle_connect():
        logger.debug("Client connected, awaiting authentication")

    @sio.on('authenticate')
    def handle_authenticate(data):
        """Client sends JWT token after connection for authentication."""
        sid = flask_request.sid
        token = data.get('token', '')

        identity = _verify_jwt_token(token, app)
        if not identity:
            emit('authenticated', {'status': 'error', 'msg': '认证失败，请重新登录'})
            return

        authenticated_users[sid] = identity
        user_number = identity.get('number', 'unknown')
        role = identity.get('role', 'employee')

        # Auto-join user room
        join_room(f'user_{user_number}')

        # Auto-join admin room if admin
        if role == 'admin':
            join_room('admins')

        emit('authenticated', {
            'status': 'ok',
            'user_number': user_number,
            'role': role
        })
        logger.info(f"User {user_number} authenticated via WebSocket")

    @sio.on('disconnect')
    def handle_disconnect():
        sid = flask_request.sid
        identity = authenticated_users.pop(sid, None)
        if identity:
            logger.debug(f"User {identity.get('number')} disconnected")

    @sio.on('join')
    def handle_join(data):
        sid = flask_request.sid
        if sid not in authenticated_users:
            emit('error', {'msg': '请先认证'})
            return
        room = data.get('room', '')
        if room:
            join_room(room)
            emit('joined', {'room': room})

    @sio.on('leave')
    def handle_leave(data):
        sid = flask_request.sid
        if sid not in authenticated_users:
            return
        room = data.get('room', '')
        if room:
            leave_room(room)
            emit('left', {'room': room})

    @sio.on('join_chat')
    def handle_join_chat(data):
        """Join the user's personal chat room (room name = user_number)."""
        sid = flask_request.sid
        if sid not in authenticated_users:
            emit('error', {'msg': '请先认证'})
            return
        user_number = data.get('user_number', '')
        if user_number:
            join_room(f'user_{user_number}')
            emit('joined_chat', {'user_number': user_number})
            logger.debug(f"User {user_number} joined chat room")

    @sio.on('leave_chat')
    def handle_leave_chat(data):
        """Leave the user's personal chat room."""
        sid = flask_request.sid
        if sid not in authenticated_users:
            return
        user_number = data.get('user_number', '')
        if user_number:
            leave_room(f'user_{user_number}')
            emit('left_chat', {'user_number': user_number})
            logger.debug(f"User {user_number} left chat room")

    @sio.on('send_message')
    def handle_send_message(data):
        """Receive a chat message via Socket.IO, persist it, and emit to recipient.

        Expected payload:
            {to_user_number, to_user_role, content}
        """
        sid = flask_request.sid
        identity = authenticated_users.get(sid)
        if not identity:
            emit('error', {'msg': '请先认证'})
            return

        sender_number = str(identity.get('number', ''))
        sender_role = str(identity.get('role', 'employee'))
        to_user_number = str(data.get('to_user_number', ''))
        to_user_role = str(data.get('to_user_role', 'employee'))
        content = (data.get('content') or '').strip()

        if not to_user_number or not content:
            emit('send_message_error', {'msg': '参数不完整'})
            return
        if len(content) > 2000:
            emit('send_message_error', {'msg': '消息内容不能超过2000字'})
            return

        try:
            from model.ChatMessage import ChatMessage
            from extension.extension import db
            from datetime import datetime

            msg = ChatMessage(
                sender_number=sender_number,
                sender_role=sender_role,
                receiver_number=to_user_number,
                receiver_role=to_user_role,
                content=content,
            )
            db.session.add(msg)
            db.session.commit()

            created_str = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')

            # Confirm to sender
            emit('message_sent', {
                'id': msg.id,
                'content': content,
                'created_at': created_str,
                'to_user_number': to_user_number,
                'to_user_role': to_user_role,
            })

            # Emit to recipient's room
            _socketio.emit('new_message', {
                'id': msg.id,
                'sender_number': sender_number,
                'sender_role': sender_role,
                'receiver_number': to_user_number,
                'receiver_role': to_user_role,
                'content': content,
                'created_at': created_str,
            }, room=f'user_{to_user_number}')

            logger.debug(f"Message {msg.id} sent from {sender_number} to {to_user_number}")
        except Exception as e:
            logger.error(f"send_message failed: {e}")
            emit('send_message_error', {'msg': '发送失败，请重试'})

    @sio.on('typing')
    def handle_typing(data):
        """Broadcast typing indicator to the recipient.

        Expected payload:
            {to_user_number}
        """
        sid = flask_request.sid
        identity = authenticated_users.get(sid)
        if not identity:
            return

        to_user_number = str(data.get('to_user_number', ''))
        if not to_user_number:
            return

        sender_number = str(identity.get('number', ''))
        sender_role = str(identity.get('role', 'employee'))

        _socketio.emit('typing', {
            'from_user_number': sender_number,
            'from_user_role': sender_role,
        }, room=f'user_{to_user_number}')

    @sio.on('mark_read')
    def handle_mark_read(data):
        """Mark messages from a peer as read and notify the sender.

        Expected payload:
            {peer_number, peer_role}
        """
        sid = flask_request.sid
        identity = authenticated_users.get(sid)
        if not identity:
            emit('error', {'msg': '请先认证'})
            return

        reader_number = str(identity.get('number', ''))
        reader_role = str(identity.get('role', 'employee'))
        peer_number = str(data.get('peer_number', ''))
        peer_role = str(data.get('peer_role', 'employee'))

        if not peer_number:
            return

        try:
            from model.ChatMessage import ChatMessage
            from extension.extension import db

            ChatMessage.query.filter_by(
                sender_number=peer_number,
                sender_role=peer_role,
                receiver_number=reader_number,
                receiver_role=reader_role,
                read=False,
            ).update({'read': True})
            db.session.commit()

            # Notify the original sender that their messages were read
            _socketio.emit('messages_read', {
                'reader_number': reader_number,
                'reader_role': reader_role,
                'sender_number': peer_number,
                'sender_role': peer_role,
            }, room=f'user_{peer_number}')

            logger.debug(f"Messages from {peer_number} marked read by {reader_number}")
        except Exception as e:
            logger.error(f"mark_read failed: {e}")


def notify_user(user_number, event, data):
    """Send a notification to a specific user."""
    if _socketio:
        try:
            _socketio.emit(event, data, room=f'user_{user_number}')
        except Exception as e:
            logger.error(f"Failed to notify user {user_number}: {e}")


def notify_admins(event, data):
    """Send a notification to all admin users."""
    if _socketio:
        try:
            _socketio.emit(event, data, room='admins')
        except Exception as e:
            logger.error(f"Failed to notify admins: {e}")


def notify_application_update(application_id, status, applicant_number):
    """Notify about application status change."""
    payload = {
        'type': 'application_update',
        'application_id': application_id,
        'status': status,
        'timestamp': datetime.utcnow().isoformat()
    }
    notify_user(applicant_number, 'notification', payload)
    notify_admins('application_update', payload)


def notify_new_application(application_id, applicant_name, data_name):
    """Notify admins about a new application submission."""
    payload = {
        'type': 'new_application',
        'application_id': application_id,
        'applicant_name': applicant_name,
        'data_name': data_name,
        'timestamp': datetime.utcnow().isoformat()
    }
    notify_admins('new_application', payload)


def notify_recall_update(proposal_id, status):
    """Notify about recall proposal status change."""
    payload = {
        'type': 'recall_update',
        'proposal_id': proposal_id,
        'status': status,
        'timestamp': datetime.utcnow().isoformat()
    }
    if _socketio:
        _socketio.emit('recall_update', payload, room='admins')


def notify_new_chat_message(message_id, sender_number, sender_role, receiver_number, receiver_role, content, created_at):
    """Emit a new_message event to the receiver's personal room."""
    if _socketio:
        try:
            payload = {
                'id': message_id,
                'sender_number': sender_number,
                'sender_role': sender_role,
                'receiver_number': receiver_number,
                'receiver_role': receiver_role,
                'content': content,
                'created_at': created_at,
            }
            _socketio.emit('new_message', payload, room=f'user_{receiver_number}')
        except Exception as e:
            logger.error(f"Failed to emit new_message: {e}")


def notify_message_read(reader_number, reader_role, sender_number, sender_role):
    """Emit a message_read event to the sender's personal room."""
    if _socketio:
        try:
            payload = {
                'reader_number': reader_number,
                'reader_role': reader_role,
                'sender_number': sender_number,
                'sender_role': sender_role,
            }
            _socketio.emit('message_read', payload, room=f'user_{sender_number}')
        except Exception as e:
            logger.error(f"Failed to emit message_read: {e}")

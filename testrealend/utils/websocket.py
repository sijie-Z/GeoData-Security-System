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
        _socketio = SocketIO(
            app,
            cors_allowed_origins='*',
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

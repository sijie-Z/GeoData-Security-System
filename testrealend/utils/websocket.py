"""WebSocket (Socket.IO) for real-time notifications."""

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
        _register_handlers(_socketio)
        logger.info("Socket.IO initialized")
    except ImportError:
        logger.warning("flask-socketio not installed, WebSocket disabled")
    return _socketio


def get_socketio():
    return _socketio


def _register_handlers(sio):
    """Register Socket.IO event handlers."""
    from flask_socketio import emit, join_room, leave_room

    @sio.on('connect')
    def handle_connect():
        logger.debug("Client connected")
        emit('connected', {'status': 'ok'})

    @sio.on('disconnect')
    def handle_disconnect():
        logger.debug("Client disconnected")

    @sio.on('join')
    def handle_join(data):
        room = data.get('room', '')
        if room:
            join_room(room)
            emit('joined', {'room': room})

    @sio.on('leave')
    def handle_leave(data):
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
    _socketio.emit('recall_update', payload, room='admins') if _socketio else None

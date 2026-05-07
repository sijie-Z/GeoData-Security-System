from flask import request
from model.Log_Info import LogInfo
from extension.extension import db


def log_action(user_number, username, action, status='成功', details=None):
    """Write an audit log entry. Commits its own transaction."""
    try:
        log = LogInfo(
            user_number=str(user_number) if user_number else '',
            username=str(username) if username else '',
            ip_address=request.remote_addr,
            action=action,
            status=status,
            details=str(details)[:500] if details else None
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass

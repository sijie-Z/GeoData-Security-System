import logging

from flask import has_request_context, request

from extension.extension import db
from model.Log_Info import LogInfo


def log_action(user_number, username, action, status="成功", details=None):
    """Write an audit log entry. Commits its own transaction.

    ``ip_address`` comes from the active request when there is one. Background
    workers (batch-embed jobs) run without a request context — they record a
    NULL ip instead of ``request.remote_addr`` raising and the audit row being
    silently dropped.
    """
    try:
        log = LogInfo(
            user_number=str(user_number) if user_number else "",
            username=str(username) if username else "",
            ip_address=request.remote_addr if has_request_context() else None,
            action=action,
            status=status,
            details=str(details)[:500] if details else None,
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        logging.error("Failed to write audit log", exc_info=True)

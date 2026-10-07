import csv
import io
import logging
from datetime import UTC, datetime

from flask import Response, request, stream_with_context
from flask_restful import Resource

from model.Log_Info import LogInfo
from utils.required import admin_required
from utils.time_fmt import parse_utc_iso

#: Hard cap for one audit-log export; beyond this the newest rows are kept and
#: the truncation is reported via the ``X-Truncated`` header + a warning log
#: (never silently).
MAX_EXPORT_ROWS = 50000
#: Chinese column captions so the CSV is directly readable in Excel.
EXPORT_COLUMNS = ["id", "时间", "用户编号", "用户名", "IP", "动作", "状态", "详情"]


def _apply_log_filters(query):
    """Apply every query parameter of ``GET /api/admin/logs`` to ``query``.

    Shared by the paginated list and the CSV export so the two always mirror
    each other. Raises ValueError for unparseable time_from/time_to.
    """
    username = request.args.get("username")
    user_number = request.args.get("user_number")
    action = request.args.get("action")
    status = request.args.get("status")

    if username:
        # Escape special LIKE characters to prevent injection
        safe_username = username.replace("%", r"\%").replace("_", r"\_")
        query = query.filter(LogInfo.username.like(f"%{safe_username}%", escape="\\"))
    if user_number:
        query = query.filter_by(user_number=user_number)
    if action:
        query = query.filter_by(action=action)
    if status:
        query = query.filter_by(status=status)

    time_from = request.args.get("time_from")
    if time_from:
        query = query.filter(LogInfo.timestamp >= parse_utc_iso(time_from))
    time_to = request.args.get("time_to")
    if time_to:
        query = query.filter(LogInfo.timestamp <= parse_utc_iso(time_to))
    return query


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
      - in: query
        name: status
        type: string
        description: Filter by status (成功/失败)
      - in: query
        name: time_from
        type: string
        description: ISO8601 lower bound on timestamp (UTC)
      - in: query
        name: time_to
        type: string
        description: ISO8601 upper bound on timestamp (UTC)
    responses:
      200: {description: Operation logs list}
    """

    @admin_required
    def get(self):
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("pageSize", 10, type=int)

        try:
            query = _apply_log_filters(LogInfo.query)
        except ValueError:
            return {"status": False, "msg": "时间参数格式非法（应为 ISO8601，如 2026-01-02T04:29:30Z）"}, 400

        pagination = query.order_by(LogInfo.timestamp.desc()).paginate(page=page, per_page=page_size, error_out=False)

        items = [
            {
                "timestamp": item.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "user_number": item.user_number,
                "username": item.username,
                "ip_address": item.ip_address,
                "action": item.action,
                "status": item.status,
                "details": item.details,
            }
            for item in pagination.items
        ]

        return {"status": True, "data": {"list": items, "total": pagination.total}}, 200


def _export_row(item):
    return [
        item.id,
        item.timestamp.strftime("%Y-%m-%d %H:%M:%S") if item.timestamp else "",
        item.user_number or "",
        item.username or "",
        item.ip_address or "",
        item.action or "",
        item.status or "",
        item.details or "",
    ]


def _csv_stream(rows):
    """Stream the CSV payload row by row: UTF-8 BOM first (so Excel opens it
    without mojibake), csv-module escaping (commas/quotes/newlines) and CRLF
    line endings."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_COLUMNS)
    yield "\ufeff" + buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)
    for item in rows:
        writer.writerow(_export_row(item))
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)


class SystemLogExportResource(Resource):
    """GET /api/admin/logs/export — streaming CSV of the audit log.

    Mirrors every filter of ``GET /api/admin/logs`` (formally the same
    ``_apply_log_filters`` helper), without pagination. Newest rows first, at
    most ``MAX_EXPORT_ROWS``; a truncation is flagged by ``X-Truncated: true``
    and a server-side warning (honest, never silent).
    """

    @admin_required
    def get(self):
        try:
            query = _apply_log_filters(LogInfo.query)
        except ValueError:
            return {"status": False, "msg": "时间参数格式非法（应为 ISO8601，如 2026-01-02T04:29:30Z）"}, 400

        total = query.count()
        truncated = total > MAX_EXPORT_ROWS
        if truncated:
            logging.warning("audit log export truncated: %s matching rows, exporting newest %s", total, MAX_EXPORT_ROWS)

        rows = query.order_by(LogInfo.timestamp.desc(), LogInfo.id.desc()).limit(MAX_EXPORT_ROWS).yield_per(500)

        filename = f"audit_logs_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv"
        response = Response(stream_with_context(_csv_stream(rows)), mimetype="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["X-Truncated"] = "true" if truncated else "false"
        response.headers["X-Total-Rows"] = str(total)
        return response

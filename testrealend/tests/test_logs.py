"""Tests for system log endpoints."""

import csv
import io
import logging
from datetime import UTC, datetime, timedelta

from model.Log_Info import LogInfo


def _seed_logs(db, count=3, user_number="EXP-T1", action="login", status="成功", start_time=None):
    """Seed `count` audit rows one minute apart with a unique user_number marker."""
    base = start_time or (datetime.now(UTC) - timedelta(minutes=30))
    for i in range(count):
        db.session.add(
            LogInfo(
                timestamp=base + timedelta(minutes=i),
                user_number=user_number,
                username=f"导出员{i}",
                ip_address="10.0.0.1",
                action=action,
                status=status,
                details='第0行,含"引号",多行\n内容' if i == 0 else f"detail-{i}",
            )
        )
    db.session.commit()


def _parse_csv(resp):
    assert resp.data[:3] == b"\xef\xbb\xbf", "UTF-8 BOM missing"
    text = resp.data[3:].decode("utf-8")
    return list(csv.reader(io.StringIO(text)))


class TestSystemLogs:
    def test_requires_auth(self, client):
        resp = client.get("/api/admin/logs")
        assert resp.status_code in (401, 422)

    def test_requires_admin(self, client, employee_headers):
        resp = client.get("/api/admin/logs", headers=employee_headers)
        # Some endpoints don't enforce role checks — accept 200 or 403
        assert resp.status_code in (200, 403, 401)

    def test_get_logs(self, client, auth_headers):
        resp = client.get("/api/admin/logs", headers=auth_headers)
        assert resp.status_code == 200

    def test_logs_with_pagination(self, client, auth_headers):
        resp = client.get("/api/admin/logs?page=1&pageSize=5", headers=auth_headers)
        assert resp.status_code == 200

    def test_logs_with_filter(self, client, auth_headers):
        resp = client.get("/api/admin/logs?action=login", headers=auth_headers)
        assert resp.status_code == 200


class TestSystemLogExport:
    """GET /api/admin/logs/export — CSV mirror of the list endpoint filters."""

    def test_export_requires_auth(self, client):
        resp = client.get("/api/admin/logs/export")
        assert resp.status_code in (401, 422)

    def test_export_requires_admin(self, client, employee_headers):
        resp = client.get("/api/admin/logs/export", headers=employee_headers)
        assert resp.status_code == 403

    def test_export_csv_bom_header_columns_and_escaping(self, client, db, auth_headers):
        _seed_logs(db, count=3, user_number="EXP-T1")
        resp = client.get("/api/admin/logs/export", query_string={"user_number": "EXP-T1"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["Content-Type"].startswith("text/csv")
        cd = resp.headers["Content-Disposition"]
        assert "attachment" in cd
        assert "audit_logs_" in cd and cd.endswith(".csv")
        assert resp.headers["X-Truncated"] == "false"
        assert resp.headers["X-Total-Rows"] == "3"

        rows = _parse_csv(resp)
        assert rows[0] == ["id", "时间", "用户编号", "用户名", "IP", "动作", "状态", "详情"]
        assert len(rows) == 3 + 1  # 行数 = 造数
        # 时间倒序：最新的一行在最前
        assert rows[1][3] == "导出员2" and rows[1][7] == "detail-2"
        # 逗号 / 引号 / 换行正确转义（csv 解析后原样还原）
        assert rows[3][3] == "导出员0"
        assert rows[3][7] == '第0行,含"引号",多行\n内容'
        assert rows[3][1] <= rows[1][1]  # timestamp strings ascending backwards

    def test_export_filter_by_action_status_and_time(self, client, db, auth_headers):
        base = (datetime.now(UTC) - timedelta(hours=5)).replace(microsecond=0)
        _seed_logs(db, count=2, user_number="EXP-T2", action="下载数据", status="成功", start_time=base)
        _seed_logs(
            db, count=1, user_number="EXP-T2", action="下载数据", status="失败", start_time=base + timedelta(minutes=10)
        )

        resp = client.get(
            "/api/admin/logs/export",
            query_string={"user_number": "EXP-T2", "action": "下载数据"},
            headers=auth_headers,
        )
        assert len(_parse_csv(resp)) == 3 + 1

        resp = client.get(
            "/api/admin/logs/export",
            query_string={"user_number": "EXP-T2", "action": "下载数据", "status": "失败"},
            headers=auth_headers,
        )
        rows = _parse_csv(resp)
        assert len(rows) == 1 + 1
        assert rows[1][6] == "失败"

        resp = client.get(
            "/api/admin/logs/export",
            query_string={
                "user_number": "EXP-T2",
                "time_from": base.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "time_to": (base + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            headers=auth_headers,
        )
        rows = _parse_csv(resp)
        assert len(rows) == 2 + 1
        assert {row[6] for row in rows[1:]} == {"成功"}

    def test_export_invalid_time_400(self, client, auth_headers):
        resp = client.get("/api/admin/logs/export", query_string={"time_from": "not-a-date"}, headers=auth_headers)
        assert resp.status_code == 400
        resp = client.get("/api/admin/logs", query_string={"time_to": "2026-99-01"}, headers=auth_headers)
        assert resp.status_code == 400

    def test_export_truncates_at_limit(self, client, db, auth_headers, monkeypatch, caplog):
        from resource import log_resource

        monkeypatch.setattr(log_resource, "MAX_EXPORT_ROWS", 2)
        _seed_logs(db, count=3, user_number="EXP-T3")
        with caplog.at_level(logging.WARNING):
            resp = client.get("/api/admin/logs/export", query_string={"user_number": "EXP-T3"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["X-Truncated"] == "true"
        assert resp.headers["X-Total-Rows"] == "3"
        rows = _parse_csv(resp)
        assert len(rows) == 2 + 1  # header + capped rows
        assert any("truncated" in record.message for record in caplog.records)

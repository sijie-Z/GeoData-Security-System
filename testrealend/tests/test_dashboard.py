"""Tests for dashboard endpoints."""


class TestAdminDashboard:
    def test_requires_auth(self, client):
        resp = client.get("/api/admin/dashboard")
        assert resp.status_code in (401, 422)

    def test_requires_admin_role(self, client, employee_headers):
        resp = client.get("/api/admin/dashboard", headers=employee_headers)
        assert resp.status_code == 403

    def test_admin_dashboard_success(self, client, auth_headers):
        resp = client.get("/api/admin/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] is True
        assert "data" in data
        d = data["data"]
        assert "total_users" in d
        assert "total_admins" in d
        assert "pending_applications" in d
        assert "today" in d
        assert "daily_trend" in d
        assert "alerts" in d
        assert "status_distribution" in d


class TestEmployeeDashboard:
    def test_requires_auth(self, client):
        resp = client.get("/api/employee/dashboard")
        assert resp.status_code in (401, 422)

    def test_employee_dashboard_success(self, client, employee_headers):
        resp = client.get("/api/employee/dashboard", headers=employee_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] is True
        assert "data" in data
        d = data["data"]
        assert "total_applications" in d
        assert "pending_applications" in d
        assert "recent_applications" in d
        assert "daily_trend" in d


class TestAdminDashboardDailyTrend:
    """daily_trend must aggregate by calendar day on SQLite as well as MySQL.

    Regression: _batch_day_counts used cast(col, Date), which SQLite evaluates
    with NUMERIC affinity — the datetime strings collapse into a single bogus
    numeric key, so every one of the 14 days read 0 even with same-day rows
    in the database (the dashboard "SQLite CAST" landmine). func.date(col)
    works on both engines.
    """

    def test_daily_trend_counts_seeded_days(self, client, db, auth_headers):
        from datetime import UTC, datetime, timedelta

        from model.Application import Application
        from model.Download_Record import DownloadRecord
        from utils.cache import invalidate_all

        now = datetime.now(UTC)
        labels = []
        for days_ago in (1, 2, 3):
            ts = (now - timedelta(days=days_ago)).replace(hour=12, minute=0, second=0, microsecond=0)
            labels.append(ts.strftime("%m-%d"))
            db.session.add(
                Application(
                    data_id=90000 + days_ago,
                    data_name=f"dash-{days_ago}",
                    data_alias=f"dash-{days_ago}",
                    data_type="raster",
                    applicant_name="Tester",
                    applicant_user_number="E001",
                    reason="daily_trend regression",
                    adm1_statu=True,
                    adm2_statu=True,
                    application_submission_time=ts,
                )
            )
            db.session.add(
                DownloadRecord(
                    application_id=90000 + days_ago,
                    data_id=90000 + days_ago,
                    data_name=f"dash-{days_ago}",
                    download_user_number="E001",
                    applicant_user_number="E001",
                    timestamp=ts,
                )
            )
        db.session.commit()
        # The dashboard response is memoized in-process (120s): drop stale
        # copies other tests may have populated, including a pre-seed one.
        invalidate_all()

        resp = client.get("/api/admin/dashboard", headers=auth_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        trend = resp.get_json()["data"]["daily_trend"]
        assert len(trend) == 14
        by_date = {row["date"]: row for row in trend}
        for label in labels:
            assert by_date[label]["applications"] >= 1, by_date[label]
            assert by_date[label]["downloads"] >= 1, by_date[label]

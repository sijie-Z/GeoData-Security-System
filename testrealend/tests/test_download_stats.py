"""Download-stats board endpoints (admin): daily series with unique downloaders,
Top users/data aggregation, fixed 7d-vs-7d comparison, days clamping and the
multi-section CSV export.
"""

import csv
import io
from datetime import UTC, datetime, timedelta

from model.Application import Application
from model.Download_Record import DownloadRecord
from model.Employee_Info import EmployeeInfo


def _today_start():
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def _seed_download(db, user="DS-U1", app_id=990001, data_name="ds-data-a", when=None):
    ts = when or (_today_start() + timedelta(hours=1))
    db.session.add(
        DownloadRecord(
            application_id=app_id,
            data_id=app_id,
            data_name=data_name,
            download_user_number=user,
            applicant_user_number=user,
            filename="artifact.zip",
            timestamp=ts,
        )
    )
    db.session.commit()


class TestDownloadStats:
    def test_requires_auth(self, client):
        resp = client.get("/api/admin/download_stats")
        assert resp.status_code in (401, 422)

    def test_requires_admin(self, client, employee_headers):
        resp = client.get("/api/admin/download_stats", headers=employee_headers)
        assert resp.status_code == 403

    def test_daily_series_length_counts_and_unique_users(self, db, client, auth_headers):
        today_start = _today_start()
        _seed_download(db, user="DS-D1", when=today_start + timedelta(hours=1))
        _seed_download(db, user="DS-D1", when=today_start + timedelta(hours=2))
        _seed_download(db, user="DS-D2", when=today_start + timedelta(hours=3))
        _seed_download(db, user="DS-D1", when=today_start - timedelta(hours=6))  # yesterday

        resp = client.get("/api/admin/download_stats?days=7", headers=auth_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
        data = resp.get_json()["data"]

        assert data["days"] == 7
        daily = data["daily"]
        assert len(daily) == 7  # 序列长度 == days
        today = daily[-1]
        assert today["downloads"] >= 3
        assert today["users"] >= 2  # DS-D1 两条只算一个独立人数
        assert daily[-2]["downloads"] >= 1  # 昨天的一条

        # 全窗口聚合和逐行真值一致
        window_start = today_start - timedelta(days=6)
        expected = DownloadRecord.query.filter(DownloadRecord.timestamp >= window_start).count()
        assert sum(d["downloads"] for d in daily) == expected

    def test_top_users_counts_and_names(self, db, client, auth_headers):
        today_start = _today_start()
        db.session.add(
            EmployeeInfo(
                employee_number="DS-U9",
                name="下载员九",
                job_number="DSJ9",
                id_number="ID900009",
                phone_number="13900000009",
                address="test",
            )
        )
        db.session.commit()
        for minute in range(4):
            _seed_download(db, user="DS-U9", when=today_start + timedelta(hours=1, minutes=minute))
        _seed_download(db, user="DS-U8", when=today_start + timedelta(hours=2))

        resp = client.get("/api/admin/download_stats?days=7", headers=auth_headers)
        top_users = {row["user_number"]: row for row in resp.get_json()["data"]["top_users"]}
        assert top_users["DS-U9"]["downloads"] == 4
        assert top_users["DS-U9"]["name"] == "下载员九"
        assert top_users["DS-U8"]["downloads"] == 1

    def test_top_data_application_dimension_with_type(self, db, client, auth_headers):
        today_start = _today_start()
        item = Application(
            data_id=990001,
            data_name="ds-dataset-A",
            data_alias="ds-A",
            data_type="Vector",
            applicant_name="T",
            applicant_user_number="DS-U7",
            reason="test",
            adm1_statu=True,
            adm2_statu=True,
        )
        db.session.add(item)
        db.session.commit()
        for minute in range(3):
            _seed_download(
                db,
                user="DS-U7",
                app_id=item.id,
                data_name="ds-dataset-A",
                when=today_start + timedelta(hours=1, minutes=minute),
            )
        _seed_download(
            db, user="DS-U6", app_id=item.id + 1, data_name="ds-dataset-B", when=today_start + timedelta(hours=2)
        )

        resp = client.get("/api/admin/download_stats?days=7", headers=auth_headers)
        top_data = {row["data_name"]: row for row in resp.get_json()["data"]["top_data"]}
        assert top_data["ds-dataset-A"]["downloads"] == 3
        assert top_data["ds-dataset-A"]["application_id"] == item.id
        assert top_data["ds-dataset-A"]["data_type"] == "vector"  # 归一化小写
        assert top_data["ds-dataset-B"]["downloads"] == 1

    def test_comparison_7v7(self, db, client, auth_headers):
        now = datetime.now(UTC)
        _seed_download(db, user="DS-C1", when=now - timedelta(minutes=5))
        _seed_download(db, user="DS-C1", when=now - timedelta(minutes=6))
        _seed_download(db, user="DS-C2", when=now - timedelta(days=9))  # 前 7 天窗口
        _seed_download(db, user="DS-C3", when=now - timedelta(days=15))  # 窗口外

        resp = client.get("/api/admin/download_stats?days=14", headers=auth_headers)
        comparison = resp.get_json()["data"]["comparison"]
        assert comparison["this_week_downloads"] >= 2
        assert comparison["last_week_downloads"] >= 1
        assert comparison["this_week_users"] >= 1
        assert comparison["last_week_users"] >= 1
        # 与逐行真值一致（含其他测试遗留行）
        lw_expected = DownloadRecord.query.filter(
            DownloadRecord.timestamp >= now - timedelta(days=14),
            DownloadRecord.timestamp < now - timedelta(days=7),
        ).count()
        assert comparison["last_week_downloads"] == lw_expected
        if comparison["last_week_downloads"]:
            expected_growth = round(
                (comparison["this_week_downloads"] - comparison["last_week_downloads"])
                / comparison["last_week_downloads"]
                * 100,
                1,
            )
            assert comparison["downloads_growth"] == expected_growth

    def test_days_clamped_to_allowed_set(self, client, db, auth_headers):
        for query_string, expected in (
            ({"days": "8"}, 30),
            ({"days": "1"}, 30),
            ({"days": "abc"}, 30),
            ({}, 30),
            ({"days": "14"}, 14),
            ({"days": "90"}, 90),
        ):
            resp = client.get("/api/admin/download_stats", query_string=query_string, headers=auth_headers)
            assert resp.status_code == 200
            data = resp.get_json()["data"]
            assert data["days"] == expected, (query_string, data["days"])
            assert len(data["daily"]) == expected

    def test_export_csv_sections_bom_and_filename(self, db, client, auth_headers):
        _seed_download(db, user="DS-E1")
        resp = client.get("/api/admin/download_stats/export?days=7", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["Content-Type"].startswith("text/csv")
        cd = resp.headers["Content-Disposition"]
        assert "attachment" in cd and "download_stats_" in cd and cd.endswith(".csv")

        assert resp.data[:3] == b"\xef\xbb\xbf"
        rows = list(csv.reader(io.StringIO(resp.data[3:].decode("utf-8"))))
        markers = [row[0] for row in rows if row]
        assert any(cell.startswith("[每日下载]") for cell in markers)
        assert any(cell.startswith("[Top 用户]") for cell in markers)
        assert any(cell.startswith("[Top 数据]") for cell in markers)
        assert any(cell.startswith("[近7天 vs 前7天]") for cell in markers)

        # 每日序列 7 行
        start = next(i for i, row in enumerate(rows) if row and row[0].startswith("[每日下载]"))
        daily_rows = rows[start + 2 : start + 2 + 7]
        assert len(daily_rows) == 7
        assert all(len(row) == 3 and row[1].isdigit() for row in daily_rows)

    def test_export_auth(self, client, employee_headers):
        assert client.get("/api/admin/download_stats/export").status_code in (401, 422)
        assert client.get("/api/admin/download_stats/export", headers=employee_headers).status_code == 403

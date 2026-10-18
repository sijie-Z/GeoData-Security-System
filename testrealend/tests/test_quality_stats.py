"""Watermark quality data layer: verification_stats aggregates, records
from/to window, admin gate, and the write-side BER/algorithm wiring.

Aggregates are asserted against hand-computed values over a fixed 5-row
fixture (NC/algorithm/BER/date spread chosen to hit distinct buckets).
"""

import io
from datetime import UTC, datetime, timedelta

import pytest
from PIL import Image

from model.watermark_verification import WatermarkVerification


def _at_days_ago(days):
    """Noon-anchored timestamp N days ago — the UTC *date* is what stats use."""
    return (datetime.now(UTC) - timedelta(days=days)).replace(hour=12, minute=0, second=0, microsecond=0)


def _seed_verifications(db):
    rows = [
        (0.95, "vector", "vector", 0.01, 0),
        (0.85, "vector", "vector", 0.02, 1),
        (0.75, "raster", "LSB", 0.05, 2),
        (0.55, "raster", None, None, 3),
        (0.35, "vector", None, None, 5),
    ]
    for nc, dtype, algo, ber_val, days in rows:
        db.session.add(
            WatermarkVerification(
                application_id=1,
                data_id=1,
                data_type=dtype,
                nc_value=nc,
                algorithm=algo,
                ber=ber_val,
                verified_by="tester",
                verified_at=_at_days_ago(days),
                ip_address="127.0.0.1",
            )
        )
    db.session.commit()


@pytest.fixture(autouse=True)
def _clean_verification_rows(db):
    """Committed rows persist across tests in the shared file-backed test DB —
    each test in this module starts from an empty watermark_verification table."""
    WatermarkVerification.query.delete()
    db.session.commit()
    yield


class TestVerificationStats:
    def test_aggregates_match_hand_computed_values(self, db, client, auth_headers):
        _seed_verifications(db)
        resp = client.get("/api/watermark/verification_stats?days=7", headers=auth_headers)
        assert resp.status_code == 200, resp.get_json()
        stats = resp.get_json()["stats"]

        assert stats["total"] == 5
        assert stats["avg_nc"] == round(3.45 / 5, 6)
        assert stats["min_nc"] == 0.35
        assert stats["max_nc"] == 0.95
        assert stats["p50_nc"] == 0.75
        assert stats["low_nc_count"] == 3

        by_type = {row["data_type"]: row for row in stats["by_data_type"]}
        assert by_type["vector"]["count"] == 3
        assert by_type["vector"]["avg_nc"] == round(2.15 / 3, 6)
        assert by_type["raster"]["count"] == 2
        assert by_type["raster"]["avg_nc"] == round(1.30 / 2, 6)

        by_algo = {row["algorithm"]: row for row in stats["by_algorithm"]}
        assert by_algo["vector"]["count"] == 2
        assert by_algo["vector"]["avg_nc"] == round(1.80 / 2, 6)
        assert by_algo["vector"]["avg_ber"] == round(0.03 / 2, 6)
        assert by_algo["LSB"]["count"] == 1 and by_algo["LSB"]["avg_ber"] == 0.05
        assert by_algo["unknown"]["count"] == 2
        assert by_algo["unknown"]["avg_ber"] is None

        hist = {row["bucket"]: row["count"] for row in stats["nc_histogram"]}
        assert len(hist) == 10
        assert hist["0.3-0.4"] == 1 and hist["0.5-0.6"] == 1 and hist["0.7-0.8"] == 1
        assert hist["0.8-0.9"] == 1 and hist["0.9-1.0"] == 1
        assert hist["0.0-0.1"] == 0 and hist["0.4-0.5"] == 0
        assert sum(hist.values()) == 5

        daily = stats["daily"]
        assert len(daily) == 7
        by_day = {row["date"]: row for row in daily}
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        assert by_day[today]["count"] == 1 and by_day[today]["avg_nc"] == 0.95
        assert by_day[_at_days_ago(1).strftime("%Y-%m-%d")]["count"] == 1
        d5 = _at_days_ago(5).strftime("%Y-%m-%d")
        assert by_day[d5]["count"] == 1 and by_day[d5]["avg_nc"] == 0.35
        d4 = _at_days_ago(4).strftime("%Y-%m-%d")
        assert by_day[d4]["count"] == 0 and by_day[d4]["avg_nc"] is None

        assert stats["range"]["min_verified_at"].startswith(d5)
        assert stats["range"]["max_verified_at"].startswith(today)

    def test_days_and_data_type_filters(self, db, client, auth_headers):
        _seed_verifications(db)
        resp = client.get("/api/watermark/verification_stats?days=3&data_type=raster", headers=auth_headers)
        stats = resp.get_json()["stats"]
        assert stats["total"] == 2
        assert stats["avg_nc"] == 0.65
        assert len(stats["daily"]) == 3
        assert {row["data_type"] for row in stats["by_data_type"]} == {"raster"}

        # days is clamped to the documented 1..365 range
        assert (
            len(
                client.get("/api/watermark/verification_stats?days=0", headers=auth_headers).get_json()["stats"][
                    "daily"
                ]
            )
            == 1
        )
        assert (
            len(
                client.get("/api/watermark/verification_stats?days=9999", headers=auth_headers).get_json()["stats"][
                    "daily"
                ]
            )
            == 365
        )

    def test_employee_forbidden(self, db, client, employee_headers):
        resp = client.get("/api/watermark/verification_stats", headers=employee_headers)
        assert resp.status_code == 403
        resp = client.get("/api/watermark/verification_stats")
        assert resp.status_code == 401


class TestVerificationRecordsWindow:
    def test_from_to_filters(self, db, client, auth_headers):
        _seed_verifications(db)
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        d3 = _at_days_ago(3).strftime("%Y-%m-%d")

        resp = client.get(f"/api/watermark/verification_records?from={today}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["pages"]["total"] == 1
        # to_dict now carries the quality columns
        assert {"algorithm", "ber", "ssim", "psnr"} <= set(resp.get_json()["data"][0].keys())

        # date-only `to` includes the whole day → day-5 and day-3 rows
        resp = client.get(f"/api/watermark/verification_records?to={d3}", headers=auth_headers)
        assert resp.get_json()["pages"]["total"] == 2

        resp = client.get(f"/api/watermark/verification_records?from={d3}&to={today}", headers=auth_headers)
        assert resp.get_json()["pages"]["total"] == 4

        # explicit datetime bounds also parse
        resp = client.get(f"/api/watermark/verification_records?from={today}T00:00:00", headers=auth_headers)
        assert resp.get_json()["pages"]["total"] == 1

    def test_invalid_window_rejected(self, db, client, auth_headers):
        resp = client.get("/api/watermark/verification_records?from=not-a-date", headers=auth_headers)
        assert resp.status_code == 400
        resp = client.get("/api/watermark/verification_records?to=2026-13-45", headers=auth_headers)
        assert resp.status_code == 400


class TestWriteSideWiring:
    def test_ori_ext_upload_records_ber_and_algorithm(self, db, client, auth_headers):
        orig = Image.new("L", (32, 32), 0)
        extracted = Image.new("L", (32, 32), 0)
        extracted.putpixel((0, 0), 255)  # exactly one flipped bit in 1024

        buf_orig, buf_ext = io.BytesIO(), io.BytesIO()
        orig.save(buf_orig, "PNG")
        extracted.save(buf_ext, "PNG")
        buf_orig.seek(0)
        buf_ext.seek(0)

        resp = client.post(
            "/api/upload/ori&ext_watermark",
            data={
                "originalFile": (buf_orig, "orig.png"),
                "extractedFile": (buf_ext, "ext.png"),
                "algorithm": "DWT",
                "host_type": "raster",
                "delivery_uuid": "11111111-2222-3333-4444-555555555555",
            },
            content_type="multipart/form-data",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.get_json()

        record = WatermarkVerification.query.order_by(WatermarkVerification.id.desc()).first()
        assert record is not None
        assert record.algorithm == "DWT"
        assert record.host_type == "raster"
        assert record.delivery_uuid == "11111111-2222-3333-4444-555555555555"
        assert record.psnr is None  # no host/stego pair at verification time
        assert record.ber == round(1 / 1024, 6)
        assert record.ssim is not None
        assert record.nc_value == round(1 - 1 / 1024, 6)

    def test_missing_optional_fields_stay_null(self, db, client, auth_headers):
        buf_orig, buf_ext = io.BytesIO(), io.BytesIO()
        Image.new("L", (16, 16), 0).save(buf_orig, "PNG")
        Image.new("L", (16, 16), 0).save(buf_ext, "PNG")
        buf_orig.seek(0)
        buf_ext.seek(0)

        resp = client.post(
            "/api/upload/ori&ext_watermark",
            data={"originalFile": (buf_orig, "orig.png"), "extractedFile": (buf_ext, "ext.png")},
            content_type="multipart/form-data",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        record = WatermarkVerification.query.order_by(WatermarkVerification.id.desc()).first()
        assert record.algorithm is None and record.delivery_uuid is None and record.host_type is None
        assert record.ber == 0.0

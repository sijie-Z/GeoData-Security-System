"""v3 delivery flow: token contract, personalized downloads, audit trail, and the
three-user acceptance path (3 FIDs / 3 artifacts / fid round-trip / copy attack).
"""

import hashlib
import io
import json
import os
import secrets
import zipfile
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from model.Application import Application
from model.download_delivery import DownloadDelivery
from model.Download_Record import DownloadRecord
from model.download_token import DownloadToken


def _make_small_shp(path, n_lines=60, n_pts=300):
    """60 lines x 300 pts = 17940 voting vertices -> lambda ~4.3 for the v10/box2 QR."""
    import geopandas as gpd
    from shapely.geometry import LineString

    rng = np.random.default_rng(42)
    lines = []
    for i in range(n_lines):
        xs = 116.0 + i * 0.01 + np.cumsum(rng.uniform(-0.001, 0.001, n_pts))
        ys = 39.0 + i * 0.01 + np.cumsum(rng.uniform(-0.001, 0.001, n_pts))
        lines.append(LineString(np.column_stack([xs, ys])))
    gdf = gpd.GeoDataFrame({"fid": range(n_lines)}, geometry=lines, crs="EPSG:4326")
    gdf.to_file(str(path))
    return str(path)


def _seed_application(db, base_path, data_id=1, alias="dlv", data_type="vector", applicant="E001"):
    item = Application(
        data_id=data_id,
        data_name=alias,
        data_alias=alias,
        data_type=data_type,
        applicant_name="Tester",
        applicant_user_number=applicant,
        reason="test",
        adm1_statu=True,
        adm2_statu=True,
        watermark_path=str(base_path) if base_path else None,
    )
    db.session.add(item)
    db.session.commit()
    return item


def _unzip_first_shp(zip_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)
    for name in sorted(os.listdir(out_dir)):
        if name.lower().endswith(".shp"):
            return os.path.join(out_dir, name)
    return None


def _extract_fid(artifact_zip, delivery, out_dir):
    """Run the verification extraction path with the delivery's stored vr_data."""
    from crypto.payload import parse_qr_text
    from resource.watermark_utils import decode_qr_from_image

    shp_path = _unzip_first_shp(artifact_zip, out_dir)
    vr_data = json.loads(delivery.vr_data)
    # scheme dispatch: "dqim1" = difference-domain QIM; no scheme = legacy extract
    if vr_data.get("scheme") == "dqim1":
        from algorithm.vector_dqim import extract_dqim as _extract

        default_side = 130
    else:
        from algorithm.extract import extract as _extract

        default_side = 45
    _shp_out, wm_png = _extract(
        shp_path,
        vr_data["vr"],
        side_length=vr_data.get("side_length") or default_side,
        output_dir=os.path.join(out_dir, "x"),
    )
    text = decode_qr_from_image(wm_png)
    assert text, "extracted watermark did not decode"
    return parse_qr_text(text)


class TestDeliveryFastPath:
    """Passthrough + mocked-embed paths: token lifecycle, contract shape, audit trail."""

    def test_passthrough_contract_download_and_record(self, db, client, employee_headers, tmp_path, monkeypatch):
        monkeypatch.setitem(client.application.config, "DELIVERY_FOLDER", str(tmp_path / "deliveries"))
        payload = tmp_path / "download_me.bin"
        payload.write_bytes(b"TOKEN-DOWNLOAD-PAYLOAD")
        item = _seed_application(db, payload)

        resp = client.post("/api/request_download_token", json={"application_id": item.id}, headers=employee_headers)
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        assert data["status"] is True
        assert data["reused"] is False
        assert set(data.keys()) >= {"status", "token", "expires_at", "reused", "delivery"}
        delivery = data["delivery"]
        assert set(delivery.keys()) == {"uuid", "fingerprint_id", "status", "created_at", "artifact_root"}
        assert delivery["status"] == "READY"
        assert delivery["created_at"].endswith("Z")  # UTC ISO, no local-time ambiguity
        assert len(delivery["fingerprint_id"]) == 32

        row = DownloadDelivery.query.filter_by(uuid=delivery["uuid"]).first()
        assert row is not None and row.status == "READY"
        assert row.algorithm == "passthrough"
        assert row.error and "跳过指纹" in row.error

        dl = client.get(f"/api/download/{data['token']}")
        assert dl.status_code == 200
        assert dl.data == b"TOKEN-DOWNLOAD-PAYLOAD"

        record = DownloadRecord.query.filter_by(delivery_id=row.delivery_id).first()
        assert record is not None, "server-side DownloadRecord missing"
        assert record.download_user_number == "E001"
        assert record.application_id == item.id
        assert record.filename == "download_me.bin"

        db.session.refresh(row)
        assert row.completed_at is not None

        # reuse is impossible after download; a second request mints a new delivery
        resp2 = client.post("/api/request_download_token", json={"application_id": item.id}, headers=employee_headers)
        assert resp2.status_code == 200
        assert resp2.get_json()["delivery"]["uuid"] != delivery["uuid"]
        assert resp2.get_json()["delivery"]["fingerprint_id"] != delivery["fingerprint_id"]

    def test_reuse_same_token_and_delivery(self, db, client, employee_headers, tmp_path, monkeypatch):
        monkeypatch.setitem(client.application.config, "DELIVERY_FOLDER", str(tmp_path / "deliveries"))
        payload = tmp_path / "reuse.bin"
        payload.write_bytes(b"REUSE")
        item = _seed_application(db, payload, data_id=2, alias="reuse")

        first = client.post("/api/request_download_token", json={"application_id": item.id}, headers=employee_headers)
        assert first.status_code == 200
        second = client.post("/api/request_download_token", json={"application_id": item.id}, headers=employee_headers)
        assert second.status_code == 200
        assert second.get_json()["reused"] is True
        assert second.get_json()["token"] == first.get_json()["token"]
        assert second.get_json()["delivery"]["uuid"] == first.get_json()["delivery"]["uuid"]

    def test_recalled_and_download_disabled_are_403(self, db, client, employee_headers, tmp_path, monkeypatch):
        monkeypatch.setitem(client.application.config, "DELIVERY_FOLDER", str(tmp_path / "deliveries"))
        payload = tmp_path / "gate.bin"
        payload.write_bytes(b"GATE")
        item = _seed_application(db, payload, data_id=3, alias="gate")

        item.is_recalled = True
        db.session.commit()
        resp = client.post("/api/request_download_token", json={"application_id": item.id}, headers=employee_headers)
        assert resp.status_code == 403
        assert "回收" in resp.get_json()["msg"]

        item.is_recalled = False
        item.download_enabled = False
        db.session.commit()
        resp = client.post("/api/request_download_token", json={"application_id": item.id}, headers=employee_headers)
        assert resp.status_code == 403
        assert "禁用" in resp.get_json()["msg"]

    def test_personalize_failure_marks_failed_and_500(self, db, client, employee_headers, tmp_path, monkeypatch):
        monkeypatch.setitem(client.application.config, "DELIVERY_FOLDER", str(tmp_path / "deliveries"))
        # data_id sentinel far beyond any autoincrement sequence: the delivery
        # fallback resolves base files via a global Shp/RasterData id lookup
        # (delivery/service.py::resolve_base_file), so a low id like 4 can
        # accidentally match a live record another test created and turn this
        # "missing base file" case into a successful passthrough (200).
        item = _seed_application(db, None, data_id=987654, alias="nofile")

        resp = client.post("/api/request_download_token", json={"application_id": item.id}, headers=employee_headers)
        assert resp.status_code == 500
        assert resp.get_json()["msg"].startswith("个性化交付生成失败")
        row = (
            DownloadDelivery.query.filter_by(application_id=item.id)
            .order_by(DownloadDelivery.delivery_id.desc())
            .first()
        )
        assert row is not None and row.status == "FAILED"
        assert "基地文件" in (row.error or "")

    def test_vector_contract_with_mocked_embed(self, db, client, employee_headers, tmp_path, monkeypatch):
        monkeypatch.setitem(client.application.config, "DELIVERY_FOLDER", str(tmp_path / "deliveries"))
        base = tmp_path / "vec.shp"
        base.write_bytes(b"SHP-BASE")
        (tmp_path / "vec.shx").write_bytes(b"SHX")
        (tmp_path / "vec.dbf").write_bytes(b"DBF")
        item = _seed_application(db, base, data_id=5, alias="vec")

        def _fake_embed(shp_path, qr_image_path, n=4, R=None, output_dir=None):
            zip_path = os.path.join(output_dir, "watermarked_vec.zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("vec.shp", b"SHP-WM")
                zf.writestr("vec.shx", b"SHX-WM")
                zf.writestr("vec.dbf", b"DBF-WM")
            return {
                "zip_path": zip_path,
                "vr": [116.0, 39.0],
                "side_length": 130,
                "capacity_report": {
                    "total_vertices": 20000,
                    "available_chunks": 20000,
                    "needed_chunks": 4177,
                    "utilization_percent": 20.9,
                    "sufficient": True,
                },
            }

        monkeypatch.setattr("delivery.service.vector_embed", _fake_embed)
        resp = client.post("/api/request_download_token", json={"application_id": item.id}, headers=employee_headers)
        assert resp.status_code == 200, resp.get_json()
        uuid = resp.get_json()["delivery"]["uuid"]
        row = DownloadDelivery.query.filter_by(uuid=uuid).first()
        assert row.algorithm == "vector"
        assert row.artifact_path.endswith(".zip")
        assert json.loads(row.vr_data)["side_length"] == 130
        dl = client.get(f"/api/download/{resp.get_json()['token']}")
        assert dl.status_code == 200
        with zipfile.ZipFile(io.BytesIO(dl.data)) as zf:
            assert sorted(zf.namelist()) == ["vec.dbf", "vec.shp", "vec.shx"]


class TestThreeUserAcceptance:
    """ADR acceptance: 3 users, 3 deliveries, 3 FIDs, correct fid round-trip, copy attack."""

    def test_three_users_three_fids_roundtrip_and_copy_attack(
        self, db, client, employee_headers, auth_headers, adm2_headers, tmp_path, monkeypatch
    ):
        monkeypatch.setitem(client.application.config, "DELIVERY_FOLDER", str(tmp_path / "deliveries"))
        shp_path = _make_small_shp(tmp_path / "small.shp")

        users = [
            (employee_headers, "E001", 101),
            (auth_headers, "admin1", 102),
            (adm2_headers, "admin2", 103),
        ]
        deliveries = []
        for headers, _user_number, data_id in users:
            item = _seed_application(db, shp_path, data_id=data_id, alias=f"prod-{data_id}")
            resp = client.post("/api/request_download_token", json={"application_id": item.id}, headers=headers)
            assert resp.status_code == 200, resp.get_json()
            body = resp.get_json()
            row = DownloadDelivery.query.filter_by(uuid=body["delivery"]["uuid"]).first()
            assert row.status == "READY", row.error
            assert row.algorithm == "vector"
            assert row.vr_data and json.loads(row.vr_data).get("side_length")
            deliveries.append((body["token"], row, headers))

        fids = [row.fingerprint_id for _t, row, _h in deliveries]
        assert len(set(fids)) == 3, fids

        artifacts = []
        for token, _row, _headers in deliveries:
            dl = client.get(f"/api/download/{token}")
            assert dl.status_code == 200
            artifacts.append(dl.data)
        digests = [hashlib.sha256(blob).hexdigest() for blob in artifacts]
        assert len(set(digests)) == 3, digests

        # fid round-trip: each artifact extracts back to its own delivery's fid
        for (_token, row, _headers), blob in zip(deliveries, artifacts):
            artifact_zip = tmp_path / f"artifact_{row.delivery_id}.zip"
            artifact_zip.write_bytes(blob)
            parsed = _extract_fid(str(artifact_zip), row, str(tmp_path / f"verify_{row.delivery_id}"))
            assert parsed["fid_hex"] == row.fingerprint_id, (parsed, row.fingerprint_id)
            assert parsed["delivery"] == row.delivery_id

        # copy attack: copy user A's artifact elsewhere and verify it via the API
        victim_token, victim_row, victim_headers = deliveries[0]
        copy_zip = tmp_path / "copy_of_A.zip"
        copy_zip.write_bytes(artifacts[0])
        resp = client.post(
            "/api/forensics/verify",
            data={"file": (io.BytesIO(copy_zip.read_bytes()), "copy_of_A.zip")},
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200, resp.get_json()
        body = resp.get_json()
        print("COPY ATTACK VERIFY:", json.dumps(body, ensure_ascii=False))
        assert body["found"] is True
        assert body["fid"] == victim_row.fingerprint_id
        assert body["delivery_uuid"] == victim_row.uuid
        assert body["artifact_root_match"] is True

        print("FIDS:", fids)
        print("SHA256:", digests)


class TestDownloadWiringHardening:
    """Round-C wiring review: legacy branch, token-path gate matrix, lambda gate,
    orphan-product cleanup after a failed personalization."""

    def _mk_token(self, db, item, delivery_id=None, **kwargs):
        token = DownloadToken(
            application_id=item.id,
            user_number="E001",
            delivery_id=delivery_id,
            expires_at=kwargs.pop("expires_at", datetime.now(UTC) + timedelta(hours=1)),
            **kwargs,
        )
        db.session.add(token)
        db.session.commit()
        return token

    def test_legacy_token_branch_downloads_and_records(self, db, client, employee_headers, tmp_path):
        """Item 13: a delivery_id=NULL token takes _deliver_legacy — file 200,
        server-side record written, recall then answers 403 on a fresh token."""
        payload = tmp_path / "legacy.bin"
        payload.write_bytes(b"LEGACY-PAYLOAD")
        item = _seed_application(db, payload, data_id=21, alias="legacy")
        token = self._mk_token(db, item)

        dl = client.get(f"/api/download/{token.token}")
        assert dl.status_code == 200
        assert dl.data == b"LEGACY-PAYLOAD"

        record = DownloadRecord.query.filter_by(application_id=item.id).order_by(DownloadRecord.id.desc()).first()
        assert record is not None, "server-side DownloadRecord missing for legacy branch"
        assert record.delivery_id is None
        assert record.filename == "legacy.bin"

        # recall 403 semantics also hold on the legacy branch
        item.is_recalled = True
        db.session.commit()
        fresh = self._mk_token(db, item)
        resp = client.get(f"/api/download/{fresh.token}")
        assert resp.status_code == 403
        assert "回收" in resp.get_json()["msg"]

    def test_token_download_gate_matrix(self, db, client, employee_headers, tmp_path):
        """Item 15: expired 403 / used 403 / FAILED delivery 404 / recalled 403 /
        download_enabled=False 403 — each gate on the token download path."""
        payload = tmp_path / "matrix.bin"
        payload.write_bytes(b"MATRIX")
        item = _seed_application(db, payload, data_id=22, alias="matrix")

        expired = self._mk_token(db, item, expires_at=datetime.now(UTC) - timedelta(minutes=1))
        resp = client.get(f"/api/download/{expired.token}")
        assert resp.status_code == 403
        assert "过期" in resp.get_json()["msg"]

        used = self._mk_token(db, item)
        used.is_used = True
        db.session.commit()
        resp = client.get(f"/api/download/{used.token}")
        assert resp.status_code == 403
        assert "已使用" in resp.get_json()["msg"]

        failed_delivery = DownloadDelivery(
            application_id=item.id,
            data_id=item.data_id,
            data_type="vector",
            user_number="E001",
            fingerprint_id=secrets.token_bytes(16).hex(),
            status="FAILED",
            created_at=datetime.now(UTC),
        )
        db.session.add(failed_delivery)
        db.session.commit()
        failed_token = self._mk_token(db, item, delivery_id=failed_delivery.delivery_id)
        resp = client.get(f"/api/download/{failed_token.token}")
        assert resp.status_code == 404
        assert "尚未就绪" in resp.get_json()["msg"]

        item.is_recalled = True
        db.session.commit()
        recalled_token = self._mk_token(db, item)
        resp = client.get(f"/api/download/{recalled_token.token}")
        assert resp.status_code == 403
        assert "回收" in resp.get_json()["msg"]

        item.is_recalled = False
        item.download_enabled = False
        db.session.commit()
        disabled_token = self._mk_token(db, item)
        resp = client.get(f"/api/download/{disabled_token.token}")
        assert resp.status_code == 403
        assert "禁用" in resp.get_json()["msg"]

    @staticmethod
    def _insufficient_embed(available, needed):
        def _fake_embed(shp_path, qr_image_path, n=4, R=None, output_dir=None):
            zip_path = os.path.join(output_dir, "watermarked_vec.zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("vec.shp", b"WM")
                zf.writestr("vec.shx", b"X")
                zf.writestr("vec.dbf", b"D")
            return {
                "zip_path": zip_path,
                "vr": [116.0, 39.0],
                "side_length": 130,
                "capacity_report": {"available_chunks": available, "needed_chunks": needed, "sufficient": True},
            }

        return _fake_embed

    def test_lambda_gate_blocks_delivery_and_removes_orphan_dir(
        self, db, client, employee_headers, tmp_path, monkeypatch
    ):
        """Item 16 (+item 4): available < 4*needed -> FAILED + 500 + no
        artifact_path and no orphan product directory left on disk."""
        folder = tmp_path / "deliveries"
        monkeypatch.setitem(client.application.config, "DELIVERY_FOLDER", str(folder))
        base = tmp_path / "cap.shp"
        base.write_bytes(b"SHP")
        (tmp_path / "cap.shx").write_bytes(b"SHX")
        (tmp_path / "cap.dbf").write_bytes(b"DBF")
        item = _seed_application(db, base, data_id=23, alias="capacity")

        monkeypatch.setattr("delivery.service.vector_embed", self._insufficient_embed(available=100, needed=100))
        resp = client.post("/api/request_download_token", json={"application_id": item.id}, headers=employee_headers)
        assert resp.status_code == 500
        assert resp.get_json()["msg"] == "个性化交付生成失败: 详见服务端日志"

        row = (
            DownloadDelivery.query.filter_by(application_id=item.id)
            .order_by(DownloadDelivery.delivery_id.desc())
            .first()
        )
        assert row.status == "FAILED"
        assert row.artifact_path is None
        assert "顶点预算不足" in (row.error or "")
        assert not (folder / row.uuid).exists(), "orphan product directory was not cleaned up"

    def test_capacity_report_missing_needed_fails_closed(self, db, client, employee_headers, tmp_path, monkeypatch):
        """Item 6: a missing needed_chunks must fail the delivery, not pass silently."""
        folder = tmp_path / "deliveries"
        monkeypatch.setitem(client.application.config, "DELIVERY_FOLDER", str(folder))
        base = tmp_path / "cap2.shp"
        base.write_bytes(b"SHP")
        (tmp_path / "cap2.shx").write_bytes(b"SHX")
        (tmp_path / "cap2.dbf").write_bytes(b"DBF")
        item = _seed_application(db, base, data_id=24, alias="capacity2")

        def _fake_embed(shp_path, qr_image_path, n=4, R=None, output_dir=None):
            zip_path = os.path.join(output_dir, "watermarked_vec.zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("vec.shp", b"WM")
            return {
                "zip_path": zip_path,
                "vr": [116.0, 39.0],
                "side_length": 130,
                "capacity_report": {"available_chunks": 20000, "sufficient": True},  # no needed_chunks
            }

        monkeypatch.setattr("delivery.service.vector_embed", _fake_embed)
        resp = client.post("/api/request_download_token", json={"application_id": item.id}, headers=employee_headers)
        assert resp.status_code == 500
        row = (
            DownloadDelivery.query.filter_by(application_id=item.id)
            .order_by(DownloadDelivery.delivery_id.desc())
            .first()
        )
        assert row.status == "FAILED"
        assert row.artifact_path is None
        assert "fail-closed" in (row.error or "")
        assert not (folder / row.uuid).exists()

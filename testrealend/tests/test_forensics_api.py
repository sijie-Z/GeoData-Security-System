"""v3 forensics endpoints: verify/trace/deliveries/anchor/keyinfo — contract shape,
tamper detection, chain broken_at, anchor root stability (acceptance 6/7).
"""

import io
import json
import os
import secrets
import zipfile
from datetime import UTC, datetime

import pytest

from crypto.keys import ensure_active_key
from crypto.payload import build_qr_v2_text
from evidence.chain import append_event
from model.Application import Application
from model.download_delivery import DownloadDelivery
from model.Download_Record import DownloadRecord
from model.evidence_event import EvidenceEvent
from model.Log_Info import LogInfo
from resource.watermark_utils import build_qr_text
from tests.test_delivery_flow import _make_small_shp

VERIFY_FIELDS = {
    "status",
    "found",
    "watermark_version",
    "fid",
    "fid_short",
    "delivery_uuid",
    "data_alias",
    "data_type",
    "issued_at",
    "signature_valid",
    "artifact_root",
    "artifact_root_match",
    "chain",
    "msg",
}

LIST_ITEM_FIELDS = {
    "uuid",
    "application_id",
    "data_id",
    "data_type",
    "user_number",
    "fingerprint_id",
    "fid_short",
    "status",
    "algorithm",
    "artifact_root",
    "created_at",
    "ready_at",
    "completed_at",
    "downloaded",
    "chain",
    "anchor",
}


def _seed_app(db, alias="fx", data_type="vector", applicant="E001", **extra):
    item = Application(
        data_id=9001,
        data_name=alias,
        data_alias=alias,
        data_type=data_type,
        applicant_name="Tester",
        applicant_user_number=applicant,
        reason="test",
        adm1_statu=True,
        adm2_statu=True,
        **extra,
    )
    db.session.add(item)
    db.session.commit()
    return item


def _seed_delivery(db, item, user="E001", status="READY", data_type="vector", with_event=True):
    delivery = DownloadDelivery(
        application_id=item.id,
        data_id=item.data_id,
        data_type=data_type,
        user_number=user,
        fingerprint_id=secrets.token_bytes(16).hex(),
        status=status,
        algorithm="vector",
        created_at=datetime.now(UTC),
        ready_at=datetime.now(UTC) if status == "READY" else None,
    )
    db.session.add(delivery)
    db.session.commit()
    if with_event:
        append_event(
            delivery.uuid,
            "DeliveryCreated",
            {"application_id": item.id, "data_id": item.data_id, "user_number": user, "fid": delivery.fingerprint_id},
        )
    return delivery


def _v2_text_for(delivery):
    kid, _ = ensure_active_key()
    return build_qr_v2_text(delivery.fingerprint_id, delivery.delivery_id, kid, int(datetime.now(UTC).timestamp()))


class TestVerifyJson:
    def test_v2_hit_contract_fields_and_no_pii(self, db, client, auth_headers):
        item = _seed_app(db, alias="file-A", adm1_name="Approver One", adm1_comment="ok")
        delivery = _seed_delivery(db, item)
        text = _v2_text_for(delivery)

        resp = client.post("/api/forensics/verify", json={"qr_text": text}, headers=auth_headers)
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        assert set(data.keys()) == VERIFY_FIELDS, set(data.keys()) ^ VERIFY_FIELDS
        assert data["status"] is True and data["found"] is True
        assert data["watermark_version"] == 2
        assert data["fid"] == delivery.fingerprint_id
        assert data["fid_short"] == delivery.fingerprint_id[:12]
        assert data["delivery_uuid"] == delivery.uuid
        assert data["data_alias"] == "file-A"
        assert data["data_type"] == "vector"
        assert data["signature_valid"] is True
        assert data["chain"]["valid"] is True and data["chain"]["length"] >= 1
        assert data["issued_at"].endswith("Z")  # UTC ISO with explicit Z suffix
        blob = json.dumps(data, ensure_ascii=False)
        for pii in ("Approver One", "Tester", "E001", "applicant"):
            assert pii not in blob, f"verify leaked {pii!r}"

    def test_tampered_payload_reports_signature_failure(self, db, client, auth_headers):
        item = _seed_app(db, alias="file-t")
        delivery = _seed_delivery(db, item)
        text = _v2_text_for(delivery)
        tampered = text[:70] + ("A" if text[70] != "A" else "B") + text[71:]

        resp = client.post("/api/forensics/verify", json={"qr_text": tampered}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["found"] is False
        assert data["watermark_version"] == 2
        assert data["signature_valid"] is False
        assert "篡改" in data["msg"]

    def test_foreign_qr_not_found(self, db, client, auth_headers):
        resp = client.post("/api/forensics/verify", json={"qr_text": "NOT-A-GDS-QR"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["found"] is False
        assert data["watermark_version"] == 0
        assert "未检测到" in data["msg"]

    def test_v1_text_hmac(self, db, client, auth_headers):
        item = _seed_app(db, alias="file-v1")
        text, _signature = build_qr_text(item, {"reason": "test"})
        resp = client.post("/api/forensics/verify", json={"qr_text": text}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["watermark_version"] == 1
        assert data["signature_valid"] is True and data["found"] is True
        assert "解码平台" in data["msg"]

        tampered = text.replace(f"ApplicantID: {item.applicant_user_number}", "ApplicantID: E999")
        resp2 = client.post("/api/forensics/verify", json={"qr_text": tampered}, headers=auth_headers)
        data2 = resp2.get_json()
        assert data2["watermark_version"] == 1
        assert data2["signature_valid"] is False and data2["found"] is False


class TestTrace:
    def test_trace_v2_provenance_complete(self, db, client, auth_headers):
        item = _seed_app(
            db,
            alias="file-trace",
            adm1_name="Approver One",
            adm1_user_number="admin1",
            adm1_approval_time=datetime.now(UTC),
            adm1_comment="looks good",
        )
        delivery = _seed_delivery(db, item)
        db.session.add(
            DownloadRecord(
                application_id=item.id,
                delivery_id=delivery.delivery_id,
                data_id=item.data_id,
                data_name=item.data_name,
                download_user_number="E001",
                download_ip="1.2.3.4",
                applicant_user_number="E001",
                filename="artifact.zip",
            )
        )
        db.session.commit()
        text = _v2_text_for(delivery)

        resp = client.post("/api/forensics/trace", json={"qr_text": text}, headers=auth_headers)
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        assert data["found"] is True and data["fid"] == delivery.fingerprint_id
        prov = data["provenance"]
        assert prov["applicant_name"] == "Tester"
        assert prov["applicant_number"] == "E001"
        assert prov["application_id"] == item.id
        assert prov["data_name"] == "file-trace"
        stages = [a["stage"] for a in prov["approvals"]]
        assert stages == ["adm1"], stages  # adm2 fields are all None -> skipped
        assert prov["approvals"][0]["name"] == "Approver One"
        assert prov["approvals"][0]["comment"] == "looks good"
        assert len(prov["downloads"]) == 1
        assert prov["downloads"][0]["delivery_uuid"] == delivery.uuid
        assert prov["downloads"][0]["user_number"] == "E001"
        assert prov["downloads"][0]["ip"] == "1.2.3.4"


class TestAuth:
    def test_employee_forbidden_on_admin_endpoints(self, db, client, employee_headers):
        for path in ("/api/forensics/verify", "/api/forensics/trace", "/api/forensics/anchor/build"):
            resp = client.post(path, json={"qr_text": "x"}, headers=employee_headers)
            assert resp.status_code == 403, (path, resp.status_code)
        resp = client.get("/api/forensics/keyinfo", headers=employee_headers)
        assert resp.status_code == 403

    def test_deliveries_list_admin_or_owner(self, db, client, auth_headers, employee_headers):
        item = _seed_app(db, alias="file-list")
        mine = _seed_delivery(db, item, user="E001")
        other = _seed_delivery(db, item, user="someone-else")

        resp = client.get(f"/api/forensics/deliveries?application_id={item.id}", headers=auth_headers)
        assert resp.status_code == 200
        deliveries = resp.get_json()["deliveries"]
        uuids = {d["uuid"] for d in deliveries}
        assert {mine.uuid, other.uuid} <= uuids
        for d in deliveries:
            assert set(d.keys()) == LIST_ITEM_FIELDS, set(d.keys()) ^ LIST_ITEM_FIELDS
            assert d["chain"]["valid"] is True
            assert set(d["anchor"].keys()) == {"status", "batch_id"}
            assert d["created_at"].endswith("Z") and d["ready_at"].endswith("Z")

        resp = client.get(f"/api/forensics/deliveries?application_id={item.id}", headers=employee_headers)
        assert resp.status_code == 200
        uuids = {d["uuid"] for d in resp.get_json()["deliveries"]}
        assert mine.uuid in uuids and other.uuid not in uuids


class TestDeliveriesDetail:
    def test_detail_shape_and_chain_broken_at(self, db, client, auth_headers):
        item = _seed_app(db, alias="file-detail")
        delivery = _seed_delivery(db, item)
        append_event(delivery.uuid, "FingerprintIssued", {"fid": delivery.fingerprint_id, "kid": 1})
        append_event(delivery.uuid, "PersonalizationCompleted", {"algorithm": "vector", "artifact_root": "ab" * 32})

        resp = client.get(f"/api/forensics/deliveries/{delivery.uuid}", headers=auth_headers)
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        assert set(data.keys()) == {"status", "delivery", "events", "chain", "anchor"}
        assert data["status"] is True
        assert data["delivery"]["uuid"] == delivery.uuid
        assert data["chain"] == {"valid": True, "length": 3, "broken_at": None}
        assert [e["seq"] for e in data["events"]] == [1, 2, 3]
        for event in data["events"]:
            assert set(event.keys()) == {"seq", "event_type", "ts", "event_hash", "kid"}
            assert event["ts"].endswith("Z")  # UTC ISO with explicit Z suffix
        assert set(data["anchor"].keys()) == {"batch_id", "status", "provider", "root_hex", "error"}

        # acceptance 6: tamper an event row -> detail reports the exact broken_at
        # (event_type feeds the re-derived event body; cbor2 tolerates trailing
        # bytes in payload_cbor, so mutating the column itself is the reliable tamper)
        victim = EvidenceEvent.query.filter_by(stream_id=delivery.uuid, seq=2).first()
        victim.event_type = victim.event_type + "!"
        db.session.commit()
        resp = client.get(f"/api/forensics/deliveries/{delivery.uuid}", headers=auth_headers)
        data = resp.get_json()
        assert data["chain"]["valid"] is False
        assert data["chain"]["broken_at"] == 2

    def test_detail_404_and_403(self, db, client, auth_headers, employee_headers):
        resp = client.get("/api/forensics/deliveries/does-not-exist", headers=auth_headers)
        assert resp.status_code == 404
        item = _seed_app(db, alias="file-own")
        other = _seed_delivery(db, item, user="someone-else")
        resp = client.get(f"/api/forensics/deliveries/{other.uuid}", headers=employee_headers)
        assert resp.status_code == 403

    def test_detail_paths_admin_only_owner_gets_whitelist(self, db, client, auth_headers, employee_headers):
        """Item 3: artifact_path / vr_data / artifact_meta_path are admin-only;
        the owner branch returns the whitelist without those three."""
        item = _seed_app(db, alias="file-priv")
        delivery = _seed_delivery(db, item, user="E001")
        delivery.artifact_path = "/srv/artifacts/secret.zip"
        delivery.artifact_meta_path = "/srv/artifacts/secret_meta.json"
        delivery.vr_data = json.dumps({"vr": [1.0, 2.0], "side_length": 45})
        db.session.commit()

        admin_view = client.get(f"/api/forensics/deliveries/{delivery.uuid}", headers=auth_headers).get_json()
        assert admin_view["delivery"]["artifact_path"] == "/srv/artifacts/secret.zip"
        assert admin_view["delivery"]["vr_data"] == delivery.vr_data
        assert admin_view["delivery"]["artifact_meta_path"] == "/srv/artifacts/secret_meta.json"

        owner_view = client.get(f"/api/forensics/deliveries/{delivery.uuid}", headers=employee_headers).get_json()
        for hidden in ("artifact_path", "vr_data", "artifact_meta_path"):
            assert hidden not in owner_view["delivery"], hidden
        assert owner_view["delivery"]["uuid"] == delivery.uuid
        assert owner_view["delivery"]["artifact_root"] == delivery.artifact_root

    def test_deliveries_list_limit_param(self, db, client, auth_headers):
        """Item 3: the list endpoint honours ?limit= (default 200, invalid -> 200)."""
        item = _seed_app(db, alias="file-lim")
        for _ in range(3):
            _seed_delivery(db, item, user="E001")

        resp = client.get(f"/api/forensics/deliveries?application_id={item.id}&limit=2", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.get_json()["deliveries"]) == 2

        resp = client.get(f"/api/forensics/deliveries?application_id={item.id}", headers=auth_headers)
        assert len(resp.get_json()["deliveries"]) == 3

        resp = client.get(f"/api/forensics/deliveries?application_id={item.id}&limit=0", headers=auth_headers)
        assert len(resp.get_json()["deliveries"]) == 3  # invalid values fall back to the default


class TestAnchor:
    def test_build_root_stable_then_changes_after_tamper(self, db, client, auth_headers, monkeypatch):
        import evidence.anchor as anchor_mod
        from evidence.anchor import NullAnchorProvider

        monkeypatch.setattr(
            "resource.forensics_resource.build_batch",
            lambda provider=None: anchor_mod.build_batch(provider=provider or NullAnchorProvider(ok=True)),
        )
        item = _seed_app(db, alias="file-anchor")
        delivery = _seed_delivery(db, item)
        append_event(delivery.uuid, "FingerprintIssued", {"fid": delivery.fingerprint_id, "kid": 1})

        first = client.post("/api/forensics/anchor/build", headers=auth_headers)
        assert first.status_code == 200, first.get_json()
        batch1 = first.get_json()["batch"]
        assert set(batch1.keys()) == {"batch_id", "root_hex", "status", "provider", "error", "explorer_url"}
        assert batch1["explorer_url"] is None  # OTS batches carry no explorer link
        assert len(batch1["root_hex"]) == 64
        assert batch1["status"] == "SUBMITTED"

        # acceptance 7a: rebuild without new events -> identical root
        second = client.post("/api/forensics/anchor/build", headers=auth_headers)
        assert second.get_json()["batch"]["root_hex"] == batch1["root_hex"]
        assert second.get_json()["batch"]["batch_id"] != batch1["batch_id"]

        # acceptance 7b: tamper an event -> rebuilt root changes. The batch root
        # is the merkle tree over the STORED event_hash column, so flip that column.
        victim = EvidenceEvent.query.filter_by(stream_id=delivery.uuid, seq=1).first()
        victim.event_hash = ("0" if victim.event_hash[0] != "0" else "1") + victim.event_hash[1:]
        db.session.commit()
        third = client.post("/api/forensics/anchor/build", headers=auth_headers)
        assert third.get_json()["batch"]["root_hex"] != batch1["root_hex"]

    def test_keyinfo(self, db, client, auth_headers):
        resp = client.get("/api/forensics/keyinfo", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert set(data.keys()) == {"status", "kid", "algo", "fingerprint", "public_key_hex"}
        assert data["status"] is True
        assert data["algo"] == "Ed25519"
        assert len(data["fingerprint"]) == 64 and len(data["public_key_hex"]) == 64

    def test_anchor_build_zero_events_400(self, db, client, auth_headers):
        EvidenceEvent.query.delete()
        db.session.commit()
        resp = client.post("/api/forensics/anchor/build", headers=auth_headers)
        assert resp.status_code == 400, resp.get_json()
        assert resp.get_json() == {"status": False, "msg": "暂无可锚定的证据事件"}


class TestVerifyUploadArtifact:
    def test_vector_zip_hit_root_match_and_byte_tamper(self, db, client, auth_headers, tmp_path, monkeypatch):
        monkeypatch.setitem(client.application.config, "DELIVERY_FOLDER", str(tmp_path / "dl"))
        shp_path = _make_small_shp(tmp_path / "upload_src.shp")
        item = _seed_app(db, alias="upload-A")
        item.watermark_path = shp_path
        # Item 17: seed PII around the application so the hit-path response can
        # be checked against a realistic leak surface.
        item.adm1_name = "Approver One"
        item.adm1_user_number = "admin1"
        item.adm1_comment = "should-not-leak"
        db.session.add(
            DownloadRecord(
                application_id=item.id,
                data_id=item.data_id,
                data_name=item.data_name,
                download_user_number="E001",
                download_ip="10.9.8.7",
                applicant_user_number="E001",
                filename="artifact.zip",
            )
        )
        db.session.commit()

        from delivery.service import get_or_create_for_token

        _token, delivery, _reused = get_or_create_for_token(item, "E001")
        assert delivery.status == "READY", delivery.error
        blob = open(delivery.artifact_path, "rb").read()

        resp = client.post(
            "/api/forensics/verify",
            data={"file": (io.BytesIO(blob), "artifact.zip")},
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        assert data["found"] is True, data
        assert data["fid"] == delivery.fingerprint_id
        assert data["delivery_uuid"] == delivery.uuid
        assert data["artifact_root_match"] is True
        leaked = json.dumps(data, ensure_ascii=False)
        for pii in ("Tester", "E001", "Approver One", "admin1", "should-not-leak", "10.9.8.7"):
            assert pii not in leaked, f"verify upload path leaked {pii!r}"

        # one-byte-class tamper: append a newline to a component (.prj) -> root differs
        tamper_dir = tmp_path / "tampered"
        tamper_dir.mkdir()
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            zf.extractall(tamper_dir)
        prj = next(tamper_dir.glob("*.prj"), None)
        assert prj is not None, "artifact has no .prj to tamper"
        prj.write_bytes(prj.read_bytes() + b"\n")
        tampered_zip = tmp_path / "tampered.zip"
        with zipfile.ZipFile(tampered_zip, "w") as zf:
            for name in sorted(os.listdir(tamper_dir)):
                zf.write(tamper_dir / name, arcname=name)

        resp2 = client.post(
            "/api/forensics/verify",
            data={"file": (io.BytesIO(tampered_zip.read_bytes()), "tampered.zip")},
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp2.status_code == 200, resp2.get_json()
        data2 = resp2.get_json()
        print("VECTOR TAMPER VERIFY:", json.dumps(data2, ensure_ascii=False))
        assert data2["found"] is True, data2
        assert data2["fid"] == delivery.fingerprint_id
        assert data2["artifact_root_match"] is False


def _zip_bytes(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, payload in entries:
            zf.writestr(name, payload)
    return buf.getvalue()


class TestUploadZipDefenses:
    """Item 14: traversal members / too many members / declared oversize all
    answer 400 and never write the extraction target directory."""

    @pytest.mark.parametrize(
        ("entries", "msg_part"),
        [
            ([("../" * 3 + "evil.txt", b"pwn")], "非法文件路径"),
            ([(f"m{i}.txt", b"x") for i in range(51)], "成员数超过 50"),
        ],
        ids=["traversal-member", "too-many-members"],
    )
    def test_malicious_zip_upload_400(self, db, client, auth_headers, entries, msg_part):
        resp = client.post(
            "/api/forensics/verify",
            data={"file": (io.BytesIO(_zip_bytes(entries)), "evil.zip")},
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert msg_part in resp.get_json()["msg"]

    def test_oversized_declared_zip_upload_400(self, db, client, auth_headers, monkeypatch):
        monkeypatch.setattr("resource.forensics_resource.ZIP_MAX_TOTAL_BYTES", 10)
        resp = client.post(
            "/api/forensics/verify",
            data={"file": (io.BytesIO(_zip_bytes([("a.bin", b"x" * 100)])), "big.zip")},
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert "解压总量" in resp.get_json()["msg"]

    @pytest.mark.parametrize(
        ("entries", "patch_limit"),
        [
            ([("../" * 3 + "evil.txt", b"pwn")], False),
            ([(f"m{i}.txt", b"x") for i in range(51)], False),
            ([("a.bin", b"x" * 100)], True),
        ],
        ids=["traversal-member", "too-many-members", "oversize"],
    )
    def test_unzip_safe_rejects_without_creating_target_dir(self, tmp_path, monkeypatch, entries, patch_limit):
        from resource.forensics_resource import _unzip_safe

        if patch_limit:
            monkeypatch.setattr("resource.forensics_resource.ZIP_MAX_TOTAL_BYTES", 10)
        evil_zip = tmp_path / "evil.zip"
        evil_zip.write_bytes(_zip_bytes(entries))
        out_dir = tmp_path / "never_written"
        with pytest.raises(ValueError):
            _unzip_safe(str(evil_zip), str(out_dir))
        assert not out_dir.exists(), "extraction target must not be created for rejected zips"

    def test_raster_upload_hit_and_root_match(self, db, client, auth_headers, tmp_path, monkeypatch):
        from tests.test_raster import _make_geotiff

        monkeypatch.setitem(client.application.config, "DELIVERY_FOLDER", str(tmp_path / "dl"))
        host = _make_geotiff(tmp_path / "host_r.tif")
        item = _seed_app(db, alias="upload-R", data_type="raster")
        item.watermark_path = str(host)
        db.session.commit()

        from delivery.service import get_or_create_for_token

        _token, delivery, _reused = get_or_create_for_token(item, "E001")
        assert delivery.status == "READY", delivery.error
        assert delivery.artifact_meta_path and os.path.isfile(delivery.artifact_meta_path)
        blob = open(delivery.artifact_path, "rb").read()

        resp = client.post(
            "/api/forensics/verify",
            data={"file": (io.BytesIO(blob), "stego.tif")},
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        print("RASTER VERIFY:", json.dumps(data, ensure_ascii=False))
        assert data["found"] is True, data
        assert data["fid"] == delivery.fingerprint_id
        assert data["data_type"] == "raster"
        assert data["artifact_root_match"] is True


class TestDeliveriesFourDimFilters:
    """§3 four-dimension search on GET /api/forensics/deliveries:
    user_number (exact) / fingerprint_id (prefix) / uuid (exact or prefix) /
    time_from-time_to (ISO8601 UTC), all combinable, employee scope enforced."""

    @staticmethod
    def _mk(db, alias, user="FX-D4", fid=None, created_at=None):
        item = _seed_app(db, alias=alias)
        delivery = DownloadDelivery(
            application_id=item.id,
            data_id=item.data_id,
            data_type="vector",
            user_number=user,
            fingerprint_id=fid or secrets.token_bytes(16).hex(),
            status="READY",
            algorithm="vector",
            created_at=created_at or datetime.now(UTC),
            ready_at=datetime.now(UTC),
        )
        db.session.add(delivery)
        db.session.commit()
        return delivery

    def test_user_number_filter_exact(self, db, client, auth_headers):
        mine = self._mk(db, "fx-d4-user-a", user="FX-D4-USER-A")
        self._mk(db, "fx-d4-user-b", user="FX-D4-USER-B")
        resp = client.get(
            "/api/forensics/deliveries", query_string={"user_number": "FX-D4-USER-A"}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert [row["uuid"] for row in resp.get_json()["deliveries"]] == [mine.uuid]
        # 精确匹配：前缀不会误命中
        resp = client.get("/api/forensics/deliveries", query_string={"user_number": "FX-D4-USER"}, headers=auth_headers)
        assert resp.get_json()["deliveries"] == []

    def test_fingerprint_id_prefix(self, db, client, auth_headers):
        delivery = self._mk(db, "fx-d4-fid", user="FX-D4-FID")
        prefix = delivery.fingerprint_id[:8]
        resp = client.get("/api/forensics/deliveries", query_string={"fingerprint_id": prefix}, headers=auth_headers)
        assert resp.status_code == 200
        rows = resp.get_json()["deliveries"]
        assert delivery.uuid in {row["uuid"] for row in rows}
        assert all(row["fingerprint_id"].startswith(prefix) for row in rows)
        # 大写输入也命中（hex 大小写不敏感）
        resp = client.get(
            "/api/forensics/deliveries", query_string={"fingerprint_id": prefix.upper()}, headers=auth_headers
        )
        assert delivery.uuid in {row["uuid"] for row in resp.get_json()["deliveries"]}

    def test_uuid_exact_and_prefix(self, db, client, auth_headers):
        delivery = self._mk(db, "fx-d4-uuid", user="FX-D4-UUID")
        resp = client.get("/api/forensics/deliveries", query_string={"uuid": delivery.uuid}, headers=auth_headers)
        assert [row["uuid"] for row in resp.get_json()["deliveries"]] == [delivery.uuid]
        resp = client.get("/api/forensics/deliveries", query_string={"uuid": delivery.uuid[:13]}, headers=auth_headers)
        assert [row["uuid"] for row in resp.get_json()["deliveries"]] == [delivery.uuid]

    def test_time_range_filter(self, db, client, auth_headers):
        jan = self._mk(db, "fx-d4-time-jan", user="FX-D4-TIME", created_at=datetime(2026, 1, 1, 6, 0, 0))
        mar = self._mk(db, "fx-d4-time-mar", user="FX-D4-TIME", created_at=datetime(2026, 3, 1, 6, 0, 0))
        resp = client.get(
            "/api/forensics/deliveries",
            query_string={
                "user_number": "FX-D4-TIME",
                "time_from": "2026-01-01T00:00:00Z",
                "time_to": "2026-01-02T00:00:00Z",
            },
            headers=auth_headers,
        )
        assert [row["uuid"] for row in resp.get_json()["deliveries"]] == [jan.uuid]
        resp = client.get(
            "/api/forensics/deliveries",
            query_string={"user_number": "FX-D4-TIME", "time_from": "2026-03-01T00:00:00Z"},
            headers=auth_headers,
        )
        assert [row["uuid"] for row in resp.get_json()["deliveries"]] == [mar.uuid]
        resp = client.get(
            "/api/forensics/deliveries",
            query_string={"user_number": "FX-D4-TIME", "time_to": "2025-12-31T00:00:00Z"},
            headers=auth_headers,
        )
        assert resp.get_json()["deliveries"] == []

    def test_combined_filters(self, db, client, auth_headers):
        match = self._mk(db, "fx-d4-comb", user="FX-D4-COMB", created_at=datetime(2026, 2, 1, 6, 0, 0))
        self._mk(db, "fx-d4-comb-other", user="FX-D4-COMB2", created_at=datetime(2026, 2, 1, 6, 0, 0))
        query = {
            "user_number": "FX-D4-COMB",
            "fingerprint_id": match.fingerprint_id[:10],
            "uuid": match.uuid[:13],
            "time_from": "2026-01-31T00:00:00Z",
            "time_to": "2026-02-02T00:00:00Z",
        }
        resp = client.get("/api/forensics/deliveries", query_string=query, headers=auth_headers)
        assert [row["uuid"] for row in resp.get_json()["deliveries"]] == [match.uuid]
        # 任一维不匹配 -> 空
        query["time_from"] = "2026-03-01T00:00:00Z"
        resp = client.get("/api/forensics/deliveries", query_string=query, headers=auth_headers)
        assert resp.get_json()["deliveries"] == []

    def test_employee_cannot_escape_own_scope(self, db, client, employee_headers):
        mine = self._mk(db, "fx-d4-emp-mine", user="E001")
        foreign = self._mk(db, "fx-d4-emp-foreign", user="FX-D4-FOREIGN")
        # 员工带他人 user_number：交集为空，不越权
        resp = client.get(
            "/api/forensics/deliveries", query_string={"user_number": "FX-D4-FOREIGN"}, headers=employee_headers
        )
        assert resp.status_code == 200
        assert resp.get_json()["deliveries"] == []
        # 员工带本人 user_number：只返回自己的
        resp = client.get("/api/forensics/deliveries", query_string={"user_number": "E001"}, headers=employee_headers)
        rows = resp.get_json()["deliveries"]
        assert mine.uuid in {row["uuid"] for row in rows}
        assert all(row["user_number"] == "E001" for row in rows)
        assert foreign.uuid not in {row["uuid"] for row in rows}

    def test_invalid_time_400(self, db, client, auth_headers):
        for query_string in ({"time_from": "not-a-date"}, {"time_to": "2026-99-01"}, {"time_from": "2026/01/01"}):
            resp = client.get("/api/forensics/deliveries", query_string=query_string, headers=auth_headers)
            assert resp.status_code == 400, (query_string, resp.status_code)

    def test_invalid_limit_still_clamped(self, db, client, auth_headers):
        self._mk(db, "fx-d4-limit-a", user="FX-D4-LIM")
        self._mk(db, "fx-d4-limit-b", user="FX-D4-LIM")
        for limit in ("0", "99999", "abc"):
            resp = client.get(
                "/api/forensics/deliveries",
                query_string={"user_number": "FX-D4-LIM", "limit": limit},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert len(resp.get_json()["deliveries"]) == 2


class TestForensicsAudit:
    """Audit trail for the leaked-copy verify/trace endpoints: exactly one
    LogInfo row per call, and ``details`` is strictly non-PII — the result
    (matched delivery uuid / 未命中) plus input type & size magnitude only.
    The raw qr_text (v1 payloads embed applicant names/ids), provenance
    blocks, comments, IPs and filenames must never reach the audit trail."""

    @staticmethod
    def _baseline_id():
        row = LogInfo.query.order_by(LogInfo.id.desc()).first()
        return row.id if row else 0

    @staticmethod
    def _new_rows(action, after_id):
        return LogInfo.query.filter(LogInfo.action == action, LogInfo.id > after_id).order_by(LogInfo.id.asc()).all()

    def test_verify_hit_writes_audit_row_without_pii(self, db, client, auth_headers):
        item = _seed_app(db, alias="fx-audit-hit", adm1_name="Approver One", adm1_user_number="admin1")
        delivery = _seed_delivery(db, item)
        text = _v2_text_for(delivery)
        baseline = self._baseline_id()

        resp = client.post("/api/forensics/verify", json={"qr_text": text}, headers=auth_headers)
        assert resp.status_code == 200

        rows = self._new_rows("泄露取证验证", baseline)
        assert len(rows) == 1, f"verify must write exactly one audit row, got {len(rows)}"
        row = rows[0]
        assert row.status == "成功"
        assert row.user_number == "admin1"  # caller identity belongs in its own columns
        details = row.details or ""
        assert delivery.uuid in details and "命中" in details
        for pii in ("Tester", "E001", "Approver One", "admin1", text):
            assert pii not in details, f"audit details leaked {pii!r}: {details}"

    def test_v1_request_pii_never_reaches_audit_details(self, db, client, auth_headers):
        item = _seed_app(db, alias="fx-audit-v1", adm1_name="Approver One", adm1_user_number="admin1")
        text, _signature = build_qr_text(item, {"reason": "audit-test"})
        baseline = self._baseline_id()

        resp = client.post("/api/forensics/verify", json={"qr_text": text}, headers=auth_headers)
        assert resp.status_code == 200

        rows = self._new_rows("泄露取证验证", baseline)
        assert len(rows) == 1
        details = rows[0].details or ""
        assert "v1" in details
        for pii in ("Tester", "E001", "Approver One", "admin1", "audit-test", "ApplicantID", "Adm1Name"):
            assert pii not in details, f"audit details leaked {pii!r}: {details}"

    def test_trace_writes_audit_row_without_provenance_pii(self, db, client, auth_headers):
        item = _seed_app(
            db,
            alias="fx-audit-trace",
            adm1_name="Approver One",
            adm1_user_number="admin1",
            adm1_approval_time=datetime.now(UTC),
            adm1_comment="looks good",
        )
        delivery = _seed_delivery(db, item)
        db.session.add(
            DownloadRecord(
                application_id=item.id,
                delivery_id=delivery.delivery_id,
                data_id=item.data_id,
                data_name=item.data_name,
                download_user_number="E001",
                download_ip="10.9.8.7",
                applicant_user_number="E001",
                filename="artifact.zip",
            )
        )
        db.session.commit()
        text = _v2_text_for(delivery)
        baseline = self._baseline_id()

        resp = client.post("/api/forensics/trace", json={"qr_text": text}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["provenance"]["applicant_name"] == "Tester"  # response is PII-rich by contract…

        rows = self._new_rows("泄露溯源查询", baseline)
        assert len(rows) == 1, f"trace must write exactly one audit row, got {len(rows)}"
        row = rows[0]
        assert row.status == "成功"
        details = row.details or ""
        assert delivery.uuid in details and "已返回溯源档案" in details
        # …the audit row is not: no names, ids, ips, comments, filenames or raw text.
        for pii in ("Tester", "E001", "Approver One", "admin1", "10.9.8.7", "looks good", "artifact.zip", text):
            assert pii not in details, f"audit details leaked {pii!r}: {details}"

    def test_miss_is_audited_as_miss(self, db, client, auth_headers):
        baseline = self._baseline_id()
        resp = client.post("/api/forensics/verify", json={"qr_text": "NOT-A-GDS-QR"}, headers=auth_headers)
        assert resp.status_code == 200

        rows = self._new_rows("泄露取证验证", baseline)
        assert len(rows) == 1
        assert "未命中" in (rows[0].details or "")

    def test_rejected_requests_audited_as_failure(self, db, client, auth_headers):
        baseline = self._baseline_id()
        resp = client.post("/api/forensics/verify", json={}, headers=auth_headers)
        assert resp.status_code == 400
        resp2 = client.post("/api/forensics/trace", json={}, headers=auth_headers)
        assert resp2.status_code == 400

        verify_rows = self._new_rows("泄露取证验证", baseline)
        trace_rows = self._new_rows("泄露溯源查询", baseline)
        assert len(verify_rows) == 1 and verify_rows[0].status == "失败"
        assert len(trace_rows) == 1 and trace_rows[0].status == "失败"

    def test_file_upload_audit_records_type_and_size_magnitude(self, db, client, auth_headers):
        baseline = self._baseline_id()
        resp = client.post(
            "/api/forensics/verify",
            data={"file": (io.BytesIO(_zip_bytes([("readme.txt", b"hi")])), "bundle.zip")},
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200

        rows = self._new_rows("泄露取证验证", baseline)
        assert len(rows) == 1
        details = rows[0].details or ""
        assert "文件类型=.zip" in details
        assert "大小≈" in details

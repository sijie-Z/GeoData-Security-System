"""Anchor center (存证中心): batch ledger endpoints, safe proof download, CIDv1.

Covers: list pagination/order/summary, detail coverage digest, proof download
happy path (OTS + EVM pack), path-traversal / missing-file guards, Etherscan URL
demux from the stored evidence pack, CIDv1 known vectors and structure, and the
``artifact_cid`` field on the PersonalizationCompleted event.
"""

import base64
import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta

import cbor2
import pytest

import evidence.anchor as anchor_mod
from delivery.artifact import CIDV1_RAW_EMPTY, cidv1_raw
from model.anchor_record import AnchorRecord
from model.Application import Application
from model.evidence_event import EvidenceEvent

ANCHOR_ITEM_FIELDS = {
    "batch_id",
    "provider",
    "status",
    "root_hex",
    "event_count",
    "head_hash",
    "proof_sha256",
    "proof_available",
    "error",
    "created_at",
    "updated_at",
    "explorer_url",
}


@pytest.fixture(autouse=True)
def _anchor_tmp_dir(tmp_path, monkeypatch):
    """Keep every proof file under tmp_path/anchors.

    Readers resolve ``evidence.anchor.ANCHOR_DIR`` live (see
    ``forensics_resource._anchors_root``), so a single patch covers both the
    writer (``build_batch``) and the new ledger/download endpoints.
    """
    root = tmp_path / "anchors"
    monkeypatch.setattr(anchor_mod, "ANCHOR_DIR", str(root))
    return root


@pytest.fixture(autouse=True)
def _clean_anchor_table(db):
    """The ``db`` fixture does not drop tables between tests — make the ledger
    deterministic (counts, ordering) and leave no rows behind for other files."""
    AnchorRecord.query.delete(synchronize_session=False)
    db.session.commit()
    yield
    AnchorRecord.query.delete(synchronize_session=False)
    db.session.commit()


def _add_record(
    db,
    *,
    provider="opentimestamps",
    status="PENDING",
    event_count=3,
    error=None,
    created_at=None,
    proof_bytes=None,
    proof_suffix=".ots",
):
    """Insert one AnchorRecord; optionally materialize its proof file on disk."""
    record = AnchorRecord(
        batch_id=str(uuid.uuid4()),
        root_hex="a" * 64,
        provider=provider,
        status=status,
        event_count=event_count,
        head_hash="b" * 64,
        error=error,
    )
    if created_at is not None:
        record.created_at = created_at
        record.updated_at = created_at
    if proof_bytes is not None:
        os.makedirs(anchor_mod.ANCHOR_DIR, exist_ok=True)
        path = os.path.join(anchor_mod.ANCHOR_DIR, f"{record.batch_id}{proof_suffix}")
        with open(path, "wb") as fh:
            fh.write(proof_bytes)
        record.proof_path = path
        record.proof_sha256 = hashlib.sha256(proof_bytes).hexdigest()
    db.session.add(record)
    db.session.commit()
    return record


def _seed_app(db, alias="ac"):
    item = Application(
        data_id=9001,
        data_name=alias,
        data_alias=alias,
        data_type="vector",
        applicant_name="Tester",
        applicant_user_number="E001",
        reason="test",
        adm1_statu=True,
        adm2_statu=True,
    )
    db.session.add(item)
    db.session.commit()
    return item


class TestAnchorLedger:
    def test_list_pagination_order_and_summary(self, db, client, auth_headers):
        t0 = datetime(2026, 1, 1, 0, 0, 0)
        r1 = _add_record(db, status="PENDING", created_at=t0)
        evm_tx = "0x" + "12" * 32
        r2 = _add_record(db, status="SUBMITTED", created_at=t0 + timedelta(hours=1), proof_bytes=b"OTS-PROOF")
        r3 = _add_record(
            db,
            provider="evm-sepolia",
            status="SUBMITTED",
            created_at=t0 + timedelta(hours=2),
            proof_suffix=".evm.json",
            proof_bytes=json.dumps({"provider": "evm-sepolia", "tx_hash": evm_tx, "chain_id": 11155111}).encode(),
        )

        resp = client.get("/api/forensics/anchors?page=1&page_size=2", headers=auth_headers)
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        assert set(data.keys()) == {"status", "anchors", "summary", "pages"}
        assert data["status"] is True
        # created_at desc: newest (EVM) first, then the OTS SUBMITTED one
        assert [a["batch_id"] for a in data["anchors"]] == [r3.batch_id, r2.batch_id]
        for item in data["anchors"]:
            assert set(item.keys()) == ANCHOR_ITEM_FIELDS, set(item.keys()) ^ ANCHOR_ITEM_FIELDS
            assert item["created_at"].endswith("Z") and item["updated_at"].endswith("Z")
        assert data["anchors"][0]["proof_available"] is True
        assert data["anchors"][0]["explorer_url"] == f"https://sepolia.etherscan.io/tx/{evm_tx}"
        assert data["anchors"][1]["explorer_url"] is None  # .ots proof carries no tx hash
        assert data["summary"] == {
            "total": 3,
            "by_provider": {"opentimestamps": 2, "evm-sepolia": 1},
            "by_status": {"PENDING": 1, "SUBMITTED": 2},
        }
        assert data["pages"] == {"total": 3, "page": 1, "page_size": 2}

        # page 2 holds the oldest record; it has no proof file at all
        resp = client.get("/api/forensics/anchors?page=2&page_size=2", headers=auth_headers)
        page2 = resp.get_json()
        assert [a["batch_id"] for a in page2["anchors"]] == [r1.batch_id]
        assert page2["anchors"][0]["proof_available"] is False
        assert page2["anchors"][0]["proof_sha256"] is None

        # clamping: page<1 -> 1, page_size>100 -> 100
        resp = client.get("/api/forensics/anchors?page=0&page_size=500", headers=auth_headers)
        pages = resp.get_json()["pages"]
        assert pages["page"] == 1 and pages["page_size"] == 100

    @pytest.mark.parametrize(
        "path",
        [
            "/api/forensics/anchors",
            "/api/forensics/anchors/does-not-exist",
            "/api/forensics/anchors/does-not-exist/proof",
        ],
    )
    def test_anchors_endpoints_admin_only(self, client, employee_headers, path):
        assert client.get(path).status_code == 401  # no token
        assert client.get(path, headers=employee_headers).status_code == 403  # non-admin

    def test_detail_shape_digest_and_404(self, db, client, auth_headers):
        record = _add_record(db, status="SUBMITTED", event_count=7, proof_bytes=b"PROOF-BYTES")
        resp = client.get(f"/api/forensics/anchors/{record.batch_id}", headers=auth_headers)
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        assert set(data.keys()) == {"status", "anchor", "events_digest"}
        assert set(data["anchor"].keys()) == ANCHOR_ITEM_FIELDS
        assert data["anchor"]["batch_id"] == record.batch_id
        assert data["anchor"]["proof_available"] is True
        assert data["anchor"]["proof_sha256"] == hashlib.sha256(b"PROOF-BYTES").hexdigest()
        # build_batch semantics: a batch snapshots ALL events as of creation, so
        # coverage is stated as count + head hash, not a per-event list.
        assert data["events_digest"] == {
            "semantics": "snapshot_all_events",
            "included_event_count": 7,
            "head_hash": "b" * 64,
        }

        resp = client.get("/api/forensics/anchors/does-not-exist", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.get_json() == {"status": False, "msg": "批次不存在"}

    def test_error_field_is_exposed(self, db, client, auth_headers):
        record = _add_record(db, status="PENDING", error="provider did not return a proof")
        resp = client.get(f"/api/forensics/anchors/{record.batch_id}", headers=auth_headers)
        assert resp.get_json()["anchor"]["error"] == "provider did not return a proof"


class TestAnchorProofDownload:
    def test_download_ots_bytes_exact(self, db, client, auth_headers):
        payload = b"\x00\x01OTS\xffPROOF\r\n"
        record = _add_record(db, status="SUBMITTED", proof_bytes=payload)
        resp = client.get(f"/api/forensics/anchors/{record.batch_id}/proof", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.data == payload
        assert f"{record.batch_id}.ots" in resp.headers["Content-Disposition"]

    def test_download_evm_pack_as_proof_json(self, db, client, auth_headers):
        pack = {
            "batch_id": "x",
            "provider": "evm-sepolia",
            "tx_hash": "0x" + "ab" * 32,
            "chain_id": 11155111,
        }
        blob = json.dumps(pack, sort_keys=True, indent=2).encode("utf-8")
        record = _add_record(db, provider="evm-sepolia", status="SUBMITTED", proof_suffix=".evm.json", proof_bytes=blob)
        resp = client.get(f"/api/forensics/anchors/{record.batch_id}/proof", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.data == blob
        assert f"{record.batch_id}.proof.json" in resp.headers["Content-Disposition"]
        assert resp.headers["Content-Type"].startswith("application/json")

    def test_download_404s(self, db, client, auth_headers, tmp_path):
        # unknown batch
        resp = client.get("/api/forensics/anchors/does-not-exist/proof", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.get_json() == {"status": False, "msg": "批次不存在"}

        # proof_path outside the anchors root (absolute escape) -> 404
        evil = tmp_path / "evil.ots"
        evil.write_bytes(b"EVIL")
        record = _add_record(db)
        record.proof_path = str(evil)
        db.session.commit()
        resp = client.get(f"/api/forensics/anchors/{record.batch_id}/proof", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.get_json() == {"status": False, "msg": "证据文件不存在"}

        # traversal via '..' -> 404
        record.proof_path = os.path.join(anchor_mod.ANCHOR_DIR, "..", "evil.ots")
        db.session.commit()
        resp = client.get(f"/api/forensics/anchors/{record.batch_id}/proof", headers=auth_headers)
        assert resp.status_code == 404

        # path inside the anchors root but file missing -> 404
        record.proof_path = os.path.join(anchor_mod.ANCHOR_DIR, "missing.ots")
        db.session.commit()
        resp = client.get(f"/api/forensics/anchors/{record.batch_id}/proof", headers=auth_headers)
        assert resp.status_code == 404

        # no proof_path at all (PENDING) -> 404
        record.proof_path = None
        db.session.commit()
        resp = client.get(f"/api/forensics/anchors/{record.batch_id}/proof", headers=auth_headers)
        assert resp.status_code == 404
        # and the ledger honestly reports proof_available=false
        detail = client.get(f"/api/forensics/anchors/{record.batch_id}", headers=auth_headers).get_json()
        assert detail["anchor"]["proof_available"] is False


class TestExplorerUrlDemux:
    def test_valid_pack_yields_url_without_provider_assumption(self, db, client, auth_headers):
        """The URL comes from the stored pack's tx_hash, not from provider == 'evm-sepolia'."""
        tx = "0x" + "cd" * 32
        record = _add_record(
            db,
            provider="some-future-evm",  # unknown provider name must not matter
            proof_suffix=".json",
            proof_bytes=json.dumps({"tx_hash": tx}).encode(),
        )
        resp = client.get(f"/api/forensics/anchors/{record.batch_id}", headers=auth_headers)
        assert resp.get_json()["anchor"]["explorer_url"] == f"https://sepolia.etherscan.io/tx/{tx}"

    @pytest.mark.parametrize(
        "blob",
        [
            b"not json at all",
            json.dumps({"provider": "evm-sepolia"}).encode(),  # no tx_hash
            json.dumps({"tx_hash": "0xshort"}).encode(),
            json.dumps({"tx_hash": "zz" * 33}).encode(),  # not hex
            json.dumps([1, 2, 3]).encode(),  # not a JSON object
        ],
    )
    def test_unreadable_packs_degrade_to_null(self, db, client, auth_headers, blob):
        record = _add_record(db, provider="evm-sepolia", proof_suffix=".evm.json", proof_bytes=blob)
        resp = client.get(f"/api/forensics/anchors/{record.batch_id}", headers=auth_headers)
        assert resp.get_json()["anchor"]["explorer_url"] is None


class TestCidv1:
    def test_known_vectors(self):
        # Spec vector: CIDv1 raw sha2-256 of the empty string — published in the
        # multiformats/IPFS docs as bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku
        assert cidv1_raw(b"") == CIDV1_RAW_EMPTY

        # Hand-derived vector: sha256(0xab * 32 bytes) =
        #   9a2db2e23f1504cd056606553ac049c5e718e8f9ce9233876df1a7a1821af885
        # CID bytes = 01 55 12 20 || digest, base32-lower multibase'ed:
        assert cidv1_raw(bytes.fromhex("ab" * 32)) == "bafkreie2fwzoepyvatgqkzqgku5masof44mor6oosizyo3pru6qyegxyqu"

    def test_structure_roundtrip(self):
        data = b"spatial-data-tracking-artifact"
        cid = cidv1_raw(data)
        assert cid[0] == "b" and cid == cid.lower()
        padded = cid[1:].upper() + "=" * (-len(cid[1:]) % 8)
        raw = base64.b32decode(padded)
        assert raw[:4] == b"\x01\x55\x12\x20"  # version 1, raw codec, sha2-256, 32 bytes
        assert raw[4:] == hashlib.sha256(data).digest()


class TestArtifactCidEvent:
    def test_personalization_completed_event_carries_artifact_cid(self, db, client, tmp_path, monkeypatch):
        """Drive a real (passthrough) delivery: the completion event must carry
        artifact_cid == cidv1_raw(bytes.fromhex(artifact_root))."""
        monkeypatch.setitem(client.application.config, "DELIVERY_FOLDER", str(tmp_path / "deliveries"))
        base = tmp_path / "asset.bin"  # non-geo -> passthrough (no embedding)
        base.write_bytes(b"SPATIAL-DATA-ARTIFACT-BYTES")
        item = _seed_app(db, alias="cid-app")
        item.watermark_path = str(base)
        db.session.commit()

        from delivery.service import get_or_create_for_token

        _token, delivery, _reused = get_or_create_for_token(item, "E001")
        assert delivery.status == "READY", delivery.error
        assert delivery.algorithm == "passthrough"

        events = EvidenceEvent.query.filter_by(stream_id=delivery.uuid, event_type="PersonalizationCompleted").all()
        assert len(events) == 1
        payload = cbor2.loads(events[0].payload_cbor)["payload"]
        assert payload["algorithm"] == "passthrough"
        assert payload["artifact_root"] == delivery.artifact_root
        assert payload["artifact_cid"] == cidv1_raw(bytes.fromhex(payload["artifact_root"]))
        assert payload["artifact_cid"].startswith("b") and payload["artifact_cid"] == payload["artifact_cid"].lower()

"""Deliveries aggregate stats endpoint (admin): counts, anchor buckets and the
batched chain-validity sample.
"""

import secrets
from datetime import UTC, datetime, timedelta

import pytest

from evidence.anchor import NullAnchorProvider, build_batch
from evidence.chain import append_event
from model.anchor_record import AnchorRecord
from model.download_delivery import DownloadDelivery
from model.Download_Record import DownloadRecord
from model.evidence_event import EvidenceEvent
from tests.test_forensics_api import _seed_app


@pytest.fixture(autouse=True)
def _clean_delivery_state(db):
    """Exact totals require a clean slate: committed rows from earlier test
    files (test_delivery_flow) persist in the shared file-backed test DB."""
    DownloadRecord.query.filter(DownloadRecord.delivery_id.isnot(None)).delete(synchronize_session=False)
    EvidenceEvent.query.delete(synchronize_session=False)
    AnchorRecord.query.delete(synchronize_session=False)
    DownloadDelivery.query.delete(synchronize_session=False)
    db.session.commit()
    yield


def _make_delivery(db, item, user, status, data_type, algorithm, ready_at):
    delivery = DownloadDelivery(
        application_id=item.id,
        data_id=item.data_id,
        data_type=data_type,
        user_number=user,
        fingerprint_id=secrets.token_bytes(16).hex(),
        status=status,
        algorithm=algorithm,
        created_at=datetime.now(UTC) - timedelta(minutes=6),
        ready_at=ready_at,
    )
    db.session.add(delivery)
    db.session.commit()
    return delivery


def _seed_three(db):
    """2 READY (vector+event, raster+event) + 1 PENDING (no event), 1 download."""
    item = _seed_app(db, alias="fx-stats")
    past = datetime.now(UTC) - timedelta(minutes=5)
    d1 = _make_delivery(db, item, "E001", "READY", "vector", "vector", ready_at=past)
    d2 = _make_delivery(db, item, "E002", "READY", "raster", "dwt", ready_at=past)
    d3 = _make_delivery(db, item, "E003", "PENDING", "raster", None, ready_at=None)
    append_event(d1.uuid, "DeliveryCreated", {"fid": d1.fingerprint_id})
    append_event(d2.uuid, "DeliveryCreated", {"fid": d2.fingerprint_id})
    db.session.add(
        DownloadRecord(
            application_id=item.id,
            delivery_id=d1.delivery_id,
            data_id=item.data_id,
            data_name=item.data_name,
            download_user_number="E001",
            download_ip="1.2.3.4",
            applicant_user_number="E001",
            filename="artifact.zip",
        )
    )
    db.session.commit()
    return d1, d2, d3


class TestDeliveryStats:
    def test_counts_match_seed(self, db, client, auth_headers):
        d1, d2, d3 = _seed_three(db)
        resp = client.get("/api/forensics/deliveries/stats", headers=auth_headers)
        assert resp.status_code == 200, resp.get_json()
        stats = resp.get_json()["stats"]

        assert stats["total"] == 3
        assert {row["status"]: row["count"] for row in stats["by_status"]} == {"READY": 2, "PENDING": 1}
        assert {row["algorithm"]: row["count"] for row in stats["by_algorithm"]} == {
            "vector": 1,
            "dwt": 1,
            "unknown": 1,
        }
        assert {row["data_type"]: row["count"] for row in stats["by_data_type"]} == {"vector": 1, "raster": 2}
        assert stats["downloaded_count"] == 1
        assert stats["anchor"] == {"submitted": 0, "pending": 0, "none": 3}

        # zero-event streams count as valid, exactly as verify_stream reports them
        assert stats["chain_checked"] == 3
        assert stats["chain_valid_count"] == 3

        recent = stats["recent"]
        assert len(recent) == 3
        assert recent[0]["uuid"] == d3.uuid  # newest first
        assert len(recent[0]["fid_short"]) == 12
        assert recent[0]["status"] == "PENDING"
        assert recent[0]["created_at"].endswith("Z")

    def test_anchor_buckets_follow_latest_anchor(self, db, client, auth_headers):
        _seed_three(db)

        build_batch(provider=NullAnchorProvider(ok=True))
        stats = client.get("/api/forensics/deliveries/stats", headers=auth_headers).get_json()["stats"]
        # both READY deliveries are covered; the PENDING one has no ready_at
        assert stats["anchor"] == {"submitted": 2, "pending": 0, "none": 1}

        # a newer PENDING anchor takes over — same "latest covering anchor"
        # semantics as _anchor_for in the deliveries list
        build_batch(provider=NullAnchorProvider(ok=False))
        stats = client.get("/api/forensics/deliveries/stats", headers=auth_headers).get_json()["stats"]
        assert stats["anchor"] == {"submitted": 0, "pending": 2, "none": 1}

        # an anchor created BEFORE a delivery became ready does not cover it
        late = _make_delivery(
            db,
            _seed_app(db, alias="fx-late"),
            "E004",
            "READY",
            "vector",
            "vector",
            ready_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        assert late is not None
        stats = client.get("/api/forensics/deliveries/stats", headers=auth_headers).get_json()["stats"]
        assert stats["anchor"] == {"submitted": 0, "pending": 2, "none": 2}

    def test_broken_chain_drops_valid_count(self, db, client, auth_headers):
        d1, _d2, _d3 = _seed_three(db)
        event = EvidenceEvent.query.filter_by(stream_id=d1.uuid).first()
        event.payload_cbor = b"tampered"
        db.session.commit()

        stats = client.get("/api/forensics/deliveries/stats", headers=auth_headers).get_json()["stats"]
        assert stats["chain_checked"] == 3
        assert stats["chain_valid_count"] == 2  # only d1's chain breaks

    def test_employee_forbidden(self, db, client, employee_headers):
        resp = client.get("/api/forensics/deliveries/stats", headers=employee_headers)
        assert resp.status_code == 403

    def test_empty_state(self, db, client, auth_headers):
        stats = client.get("/api/forensics/deliveries/stats", headers=auth_headers).get_json()["stats"]
        assert stats["total"] == 0
        assert stats["downloaded_count"] == 0
        assert stats["anchor"] == {"submitted": 0, "pending": 0, "none": 0}
        assert stats["chain_checked"] == 0 and stats["chain_valid_count"] == 0
        assert stats["recent"] == []

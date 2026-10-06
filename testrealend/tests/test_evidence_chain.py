"""Tests for the evidence hash chain, merkle tree and batch anchoring."""

import hashlib
import os
import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from crypto import canonical
from crypto.keys import ensure_active_key
from evidence.anchor import NullAnchorProvider, build_batch
from evidence.chain import GENESIS_HASH, append_event, get_events, verify_stream
from evidence.constants import DOMAIN_EVENT
from evidence.merkle import merkle_root
from model.evidence_event import EvidenceEvent
from model.key_registry import KeyRegistry


def _stream_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


class TestChain:
    def test_append_and_verify_stream(self, db):
        stream_id = _stream_id("chain")
        e1 = append_event(stream_id, "DELIVERY_CREATED", {"n": 1})
        e2 = append_event(stream_id, "ARTIFACT_SEALED", {"n": 2})
        e3 = append_event(stream_id, "DELIVERY_READY", {"n": 3})

        events = get_events(stream_id)
        assert [event.seq for event in events] == [1, 2, 3]
        assert e1.prev_hash == GENESIS_HASH
        assert e2.prev_hash == e1.event_hash
        assert e3.prev_hash == e2.event_hash

        result = verify_stream(stream_id)
        assert result["valid"] is True
        assert result["length"] == 3
        assert result["head_hash"] == e3.event_hash
        assert result["broken_at"] is None
        assert result["reason"] is None

    def test_same_second_identical_genesis_events_across_streams_do_not_collide(self, db):
        """Regression: two streams writing identical genesis content in the same
        second must both persist with distinct event_hash values (stream + seq
        are bound into the body that the hash commits to)."""
        ts = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
        stream_a = _stream_id("chain-genesis-a")
        stream_b = _stream_id("chain-genesis-b")

        e1 = append_event(stream_a, "EVT", {"same": True}, ts=ts)
        e2 = append_event(stream_b, "EVT", {"same": True}, ts=ts)

        assert e1.event_hash != e2.event_hash
        assert verify_stream(stream_a)["valid"] is True
        assert verify_stream(stream_b)["valid"] is True

    def test_tampered_payload_detected_at_second_event(self, db):
        stream_id = _stream_id("chain-tamper")
        for i in range(3):
            append_event(stream_id, "EVT", {"i": i})

        row = get_events(stream_id)[1]
        row.payload_cbor = b"\x00" + bytes(row.payload_cbor[1:])
        db.session.commit()

        result = verify_stream(stream_id)
        assert result["valid"] is False
        assert result["broken_at"] == 2
        assert result["length"] == 3

    def test_tampered_last_signature_invalid(self, db):
        stream_id = _stream_id("chain-sig")
        for i in range(3):
            append_event(stream_id, "EVT", {"i": i})

        row = get_events(stream_id)[-1]
        signature = bytearray(row.signature)
        signature[0] ^= 0x01
        row.signature = bytes(signature)
        db.session.commit()

        result = verify_stream(stream_id)
        assert result["valid"] is False
        assert result["broken_at"] == 3

    def test_empty_stream_is_valid_and_empty(self, db):
        result = verify_stream(_stream_id("chain-empty"))
        assert result == {"valid": True, "length": 0, "head_hash": None, "broken_at": None, "reason": None}

    def test_aware_non_utc_ts_normalised_to_utc_and_hashes_as_utc_equivalent(self, db):
        """C-1: a +08:00 ts must be stored as naive UTC and commit to exactly the
        same epoch as the equivalent UTC instant (regression: 8h epoch skew made
        an intact chain report broken)."""
        stream_id = _stream_id("chain-tz")
        aware = datetime(2026, 1, 2, 10, 0, tzinfo=timezone(timedelta(hours=8)))
        e1 = append_event(stream_id, "EVT", {"i": 1}, ts=aware)

        assert e1.ts.tzinfo is None
        assert e1.ts == datetime(2026, 1, 2, 2, 0)
        assert verify_stream(stream_id)["valid"] is True

        equivalent_utc = datetime(2026, 1, 2, 2, 0, tzinfo=UTC)
        expected_body = canonical.dumps(
            {"stream": stream_id, "seq": 1, "type": "EVT", "payload": {"i": 1}, "ts": int(equivalent_utc.timestamp())}
        )
        expected_hash = hashlib.sha256(DOMAIN_EVENT + bytes.fromhex(GENESIS_HASH) + expected_body).hexdigest()
        assert e1.event_hash == expected_hash

    def test_naive_ts_kept_naive_and_interpreted_as_utc(self, db):
        """C-1: naive input is interpreted as UTC and stays naive in the column."""
        stream_id = _stream_id("chain-naive")
        naive = datetime(2026, 1, 2, 3, 0, 0)
        e1 = append_event(stream_id, "EVT", {"i": 1}, ts=naive)
        assert e1.ts.tzinfo is None
        assert e1.ts == naive
        assert verify_stream(stream_id)["valid"] is True

    @staticmethod
    def _register_other_key(db) -> int:
        other = ed25519.Ed25519PrivateKey.generate()
        raw = other.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        row = KeyRegistry(name="other-key", public_key=raw, status="active", created_at=datetime.now(UTC))
        db.session.add(row)
        db.session.commit()
        return row.kid

    def test_explicit_kid_mismatch_raises_and_writes_nothing(self, db):
        """C-3: an explicit kid for a different registered key must fail closed."""
        other_kid = self._register_other_key(db)
        stream_id = _stream_id("chain-kid-mismatch")
        before = EvidenceEvent.query.count()
        with pytest.raises(ValueError):
            append_event(stream_id, "EVT", {"i": 1}, kid=other_kid)
        assert EvidenceEvent.query.count() == before
        assert get_events(stream_id) == []

    def test_unknown_explicit_kid_raises_and_writes_nothing(self, db):
        """C-3: an explicit kid that is not registered must fail closed."""
        stream_id = _stream_id("chain-kid-unknown")
        before = EvidenceEvent.query.count()
        with pytest.raises(ValueError):
            append_event(stream_id, "EVT", {"i": 1}, kid=10**6)
        assert EvidenceEvent.query.count() == before
        assert get_events(stream_id) == []

    def test_explicit_correct_kid_accepted(self, db):
        """C-3 positive: the active kid is a valid explicit argument."""
        active_kid, _private_key = ensure_active_key()
        stream_id = _stream_id("chain-kid-ok")
        e1 = append_event(stream_id, "EVT", {"i": 1}, kid=active_kid)
        assert e1.kid == active_kid
        assert verify_stream(stream_id)["valid"] is True


class TestMerkle:
    H1, H2, H3, H4 = "aa" * 32, "bb" * 32, "cc" * 32, "dd" * 32

    @staticmethod
    def _leaf(event_hash: str) -> bytes:
        return hashlib.sha256(b"GDS-LEAF-V1" + bytes.fromhex(event_hash)).digest()

    @staticmethod
    def _parent(left: bytes, right: bytes) -> bytes:
        return hashlib.sha256(b"GDS-MERKLE-V1" + left + right).digest()

    def test_empty_returns_none(self):
        assert merkle_root([]) is None

    def test_single_leaf_is_leaf_hash(self):
        assert merkle_root([self.H1]) == self._leaf(self.H1).hex()

    def test_two_three_four_leaves_match_hand_computation(self):
        leaf, parent = self._leaf, self._parent
        expected2 = parent(leaf(self.H1), leaf(self.H2)).hex()
        expected3 = parent(parent(leaf(self.H1), leaf(self.H2)), parent(leaf(self.H3), leaf(self.H3))).hex()
        expected4 = parent(parent(leaf(self.H1), leaf(self.H2)), parent(leaf(self.H3), leaf(self.H4))).hex()
        assert merkle_root([self.H1, self.H2]) == expected2
        assert merkle_root([self.H1, self.H2, self.H3]) == expected3
        assert merkle_root([self.H1, self.H2, self.H3, self.H4]) == expected4

    def test_deterministic_and_sensitive_to_input(self):
        assert merkle_root([self.H1, self.H2, self.H3]) == merkle_root([self.H1, self.H2, self.H3])
        assert merkle_root([self.H1, self.H2, self.H3]) != merkle_root([self.H1, self.H2, self.H4])


class TestAnchoring:
    def test_null_provider_success_and_failure(self, db):
        stream_id = _stream_id("anchor")
        append_event(stream_id, "EVT", {"ok": True})

        record = build_batch(NullAnchorProvider(ok=True))
        assert record.status == "SUBMITTED"
        assert record.provider == "null"
        assert record.error is None
        assert record.root_hex and len(record.root_hex) == 64
        assert record.proof_path and os.path.exists(record.proof_path)

        failed = build_batch(NullAnchorProvider(ok=False))
        assert failed.status == "PENDING"
        assert failed.error
        assert failed.proof_path is None

    def test_replay_without_new_events_yields_same_root(self, db):
        stream_id = _stream_id("anchor-replay")
        append_event(stream_id, "EVT", {"i": 1})
        append_event(stream_id, "EVT", {"i": 2})

        first = build_batch(NullAnchorProvider(ok=True))
        second = build_batch(NullAnchorProvider(ok=True))
        assert first.root_hex == second.root_hex

    def test_root_matches_manual_merkle_over_all_events(self, db):
        stream_id = _stream_id("anchor-manual")
        append_event(stream_id, "EVT", {"x": 1})
        record = build_batch(NullAnchorProvider(ok=True))

        events = EvidenceEvent.query.order_by(EvidenceEvent.stream_id.asc(), EvidenceEvent.seq.asc()).all()
        assert record.root_hex == merkle_root([event.event_hash for event in events])

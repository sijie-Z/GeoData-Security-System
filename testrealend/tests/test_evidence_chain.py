"""Tests for the evidence hash chain, merkle tree and batch anchoring."""

import hashlib
import os
import uuid

from evidence.anchor import NullAnchorProvider, build_batch
from evidence.chain import GENESIS_HASH, append_event, get_events, verify_stream
from evidence.merkle import merkle_root
from model.evidence_event import EvidenceEvent


def _stream_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _payload(stream_id: str, **fields) -> dict:
    """Stream-tagged payload, keeping genesis hashes unique across streams.

    The chain hash commits to (type, payload, second-precision ts, prev_hash)
    only, so two genesis events with identical content within the same second
    would produce the same event_hash (UNIQUE violation) — tagging payloads
    with the unique stream id avoids that.
    """
    return {"stream": stream_id, **fields}


class TestChain:
    def test_append_and_verify_stream(self, db):
        stream_id = _stream_id("chain")
        e1 = append_event(stream_id, "DELIVERY_CREATED", _payload(stream_id, n=1))
        e2 = append_event(stream_id, "ARTIFACT_SEALED", _payload(stream_id, n=2))
        e3 = append_event(stream_id, "DELIVERY_READY", _payload(stream_id, n=3))

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

    def test_tampered_payload_detected_at_second_event(self, db):
        stream_id = _stream_id("chain-tamper")
        for i in range(3):
            append_event(stream_id, "EVT", _payload(stream_id, i=i))

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
            append_event(stream_id, "EVT", _payload(stream_id, i=i))

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
        append_event(stream_id, "EVT", _payload(stream_id, ok=True))

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
        append_event(stream_id, "EVT", _payload(stream_id, i=1))
        append_event(stream_id, "EVT", _payload(stream_id, i=2))

        first = build_batch(NullAnchorProvider(ok=True))
        second = build_batch(NullAnchorProvider(ok=True))
        assert first.root_hex == second.root_hex

    def test_root_matches_manual_merkle_over_all_events(self, db):
        stream_id = _stream_id("anchor-manual")
        append_event(stream_id, "EVT", _payload(stream_id, x=1))
        record = build_batch(NullAnchorProvider(ok=True))

        events = EvidenceEvent.query.order_by(EvidenceEvent.stream_id.asc(), EvidenceEvent.seq.asc()).all()
        assert record.root_hex == merkle_root([event.event_hash for event in events])

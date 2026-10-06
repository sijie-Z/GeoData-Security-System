"""Tests for the evidence hash chain, merkle tree and batch anchoring."""

import hashlib
import os
import struct
import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from crypto import canonical
from crypto.keys import ensure_active_key
from evidence.anchor import AnchorProvider, NullAnchorProvider, build_batch
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

    def test_column_by_column_tampering_is_detected(self, db):
        """§3: changing any single stored column must break verification at that event."""
        cases = {
            "stream_id": lambda event: setattr(event, "stream_id", "moved-" + event.stream_id),
            "seq": lambda event: setattr(event, "seq", 99),
            "event_type": lambda event: setattr(event, "event_type", event.event_type + "!"),
            "ts": lambda event: setattr(event, "ts", event.ts + timedelta(hours=1)),
            "prev_hash": lambda event: setattr(event, "prev_hash", "f" * 64),
        }
        for name, mutate in cases.items():
            stream_id = _stream_id(f"chain-tamper-{name}")
            for i in range(3):
                append_event(stream_id, "EVT", {"i": i})
            mutate(get_events(stream_id)[1])
            db.session.commit()
            result = verify_stream(stream_id)
            assert result["valid"] is False, name
            assert result["broken_at"] == 2, (name, result)

    def test_kid_column_tampering_is_detected(self, db):
        """§3: switching the kid to another registered key must break the signature check."""
        other_kid = self._register_other_key(db)
        stream_id = _stream_id("chain-tamper-kid")
        for i in range(3):
            append_event(stream_id, "EVT", {"i": i})
        get_events(stream_id)[1].kid = other_kid
        db.session.commit()
        result = verify_stream(stream_id)
        assert result["valid"] is False
        assert result["broken_at"] == 2
        assert "signature" in result["reason"]

    def test_tampered_payload_cbor_with_trailing_garbage_detected(self, db):
        """B-5: appending bytes after the CBOR event body must break the chain
        (previously the decoder silently ignored trailing garbage)."""
        stream_id = _stream_id("chain-trailing")
        for i in range(3):
            append_event(stream_id, "EVT", {"i": i})

        row = get_events(stream_id)[1]
        row.payload_cbor = bytes(row.payload_cbor) + b"\xff\x00trailing-garbage"
        db.session.commit()

        result = verify_stream(stream_id)
        assert result["valid"] is False
        assert result["broken_at"] == 2
        assert "trailing bytes" in result["reason"]

    @pytest.mark.parametrize(
        "corrupt",
        [
            pytest.param(lambda event: setattr(event, "payload_cbor", None), id="payload_cbor-null"),
            pytest.param(lambda event: setattr(event, "ts", None), id="ts-null"),
            pytest.param(lambda event: setattr(event, "signature", b"\x00"), id="short-signature"),
            pytest.param(lambda event: setattr(event, "kid", 999999), id="unknown-kid"),
        ],
    )
    def test_corrupt_rows_report_broken_without_raising(self, db, corrupt):
        """§3: physically corrupt rows must degrade to valid=False, never an exception."""
        stream_id = _stream_id("chain-corrupt")
        for i in range(3):
            append_event(stream_id, "EVT", {"i": i})
        corrupt(get_events(stream_id)[1])
        db.session.commit()

        result = verify_stream(stream_id)  # must not raise
        assert result["valid"] is False
        assert result["broken_at"] == 2
        assert result["reason"]


class TestMerkle:
    H1, H2, H3, H4 = "aa" * 32, "bb" * 32, "cc" * 32, "dd" * 32
    H5, H6, H7 = "ee" * 32, "ff" * 32, "11" * 32

    @staticmethod
    def _leaf(event_hash: str, total: int, index: int) -> bytes:
        # D-1: leaf = sha256(DOMAIN_LEAF || uint32be(n) || uint32be(i) || raw hash)
        return hashlib.sha256(b"GDS-LEAF-V1" + struct.pack(">II", total, index) + bytes.fromhex(event_hash)).digest()

    @staticmethod
    def _parent(left: bytes, right: bytes) -> bytes:
        return hashlib.sha256(b"GDS-MERKLE-V1" + left + right).digest()

    def test_empty_returns_none(self):
        assert merkle_root([]) is None

    def test_single_leaf_is_leaf_hash(self):
        assert merkle_root([self.H1]) == self._leaf(self.H1, 1, 0).hex()

    def test_two_three_four_leaves_match_hand_computation(self):
        leaf, parent = self._leaf, self._parent
        expected2 = parent(leaf(self.H1, 2, 0), leaf(self.H2, 2, 1)).hex()
        expected3 = parent(
            parent(leaf(self.H1, 3, 0), leaf(self.H2, 3, 1)),
            parent(leaf(self.H3, 3, 2), leaf(self.H3, 3, 2)),
        ).hex()
        expected4 = parent(
            parent(leaf(self.H1, 4, 0), leaf(self.H2, 4, 1)),
            parent(leaf(self.H3, 4, 2), leaf(self.H4, 4, 3)),
        ).hex()
        assert merkle_root([self.H1, self.H2]) == expected2
        assert merkle_root([self.H1, self.H2, self.H3]) == expected3
        assert merkle_root([self.H1, self.H2, self.H3, self.H4]) == expected4

    def test_three_leaves_vs_duplicated_fourth_have_different_roots(self):
        """D-1 regression: root([A,B,C]) == root([A,B,C,C]) before the leaf domain
        bound the batch size and position; they must now differ."""
        assert merkle_root([self.H1, self.H2, self.H3]) != merkle_root([self.H1, self.H2, self.H3, self.H3])

    def test_five_six_seven_leaves_match_hand_computation(self):
        """n>4 exercises the duplicate-last-node merge branch at multiple depths."""
        leaf, parent = self._leaf, self._parent

        n = 5
        levels = [leaf(h, n, i) for i, h in enumerate([self.H1, self.H2, self.H3, self.H4, self.H5])]
        level2 = [parent(levels[0], levels[1]), parent(levels[2], levels[3]), parent(levels[4], levels[4])]
        expected5 = parent(parent(level2[0], level2[1]), parent(level2[2], level2[2])).hex()
        assert merkle_root([self.H1, self.H2, self.H3, self.H4, self.H5]) == expected5

        n = 6
        levels = [leaf(h, n, i) for i, h in enumerate([self.H1, self.H2, self.H3, self.H4, self.H5, self.H6])]
        level2 = [parent(levels[0], levels[1]), parent(levels[2], levels[3]), parent(levels[4], levels[5])]
        level3 = [parent(level2[0], level2[1]), parent(level2[2], level2[2])]
        expected6 = parent(level3[0], level3[1]).hex()
        assert merkle_root([self.H1, self.H2, self.H3, self.H4, self.H5, self.H6]) == expected6

        n = 7
        levels = [leaf(h, n, i) for i, h in enumerate([self.H1, self.H2, self.H3, self.H4, self.H5, self.H6, self.H7])]
        level2 = [parent(levels[0], levels[1]), parent(levels[2], levels[3]), parent(levels[4], levels[5])]
        level2.append(parent(levels[6], levels[6]))
        level3 = [parent(level2[0], level2[1]), parent(level2[2], level2[3])]
        expected7 = parent(level3[0], level3[1]).hex()
        assert merkle_root([self.H1, self.H2, self.H3, self.H4, self.H5, self.H6, self.H7]) == expected7

    def test_invalid_event_hash_inputs_raise_value_error(self):
        """E-1: None / non-hex / wrong-length input must raise a clean ValueError."""
        for bad in (None, "zz" * 32, "abcd", b"aa" * 32, 123):
            with pytest.raises(ValueError, match="invalid event hash"):
                merkle_root([bad])

    def test_deterministic_and_sensitive_to_input(self):
        assert merkle_root([self.H1, self.H2, self.H3]) == merkle_root([self.H1, self.H2, self.H3])
        assert merkle_root([self.H1, self.H2, self.H3]) != merkle_root([self.H1, self.H2, self.H4])


class TestAnchoring:
    def test_null_provider_success_and_failure(self, db):
        EvidenceEvent.query.delete()
        db.session.commit()
        stream_id = _stream_id("anchor")
        append_event(stream_id, "EVT", {"ok": True})

        record = build_batch(NullAnchorProvider(ok=True))
        assert record.status == "SUBMITTED"
        assert record.provider == "null"
        assert record.error is None
        assert record.root_hex and len(record.root_hex) == 64
        assert record.proof_path and os.path.exists(record.proof_path)
        # C-2: completeness binding matches the table content at build time
        assert record.event_count == 1
        assert record.head_hash == EvidenceEvent.query.order_by(EvidenceEvent.id.desc()).first().event_hash
        # E-3: the stored proof digest matches the file on disk
        with open(record.proof_path, "rb") as fh:
            assert record.proof_sha256 == hashlib.sha256(fh.read()).hexdigest()

        failed = build_batch(NullAnchorProvider(ok=False))
        assert failed.status == "PENDING"
        assert failed.error
        assert failed.proof_path is None
        assert failed.proof_sha256 is None

    def test_replay_without_new_events_yields_same_root_count_and_head(self, db):
        stream_id = _stream_id("anchor-replay")
        append_event(stream_id, "EVT", {"i": 1})
        append_event(stream_id, "EVT", {"i": 2})

        first = build_batch(NullAnchorProvider(ok=True))
        second = build_batch(NullAnchorProvider(ok=True))
        assert first.root_hex == second.root_hex
        assert first.event_count == second.event_count
        assert first.head_hash == second.head_hash

    def test_batch_order_is_insertion_id_not_collation(self, db):
        """D-2: the batch order is EvidenceEvent.id (insertion order), not the
        (stream_id, seq) text order, which flips with the DB collation."""
        EvidenceEvent.query.delete()
        db.session.commit()
        stream_z = _stream_id("ZZ")  # sorts after the lowercase stream under BINARY collation
        stream_a = _stream_id("aa")
        e_z1 = append_event(stream_z, "EVT", {"i": 1})
        e_a1 = append_event(stream_a, "EVT", {"i": 1})
        e_z2 = append_event(stream_z, "EVT", {"i": 2})

        record = build_batch(NullAnchorProvider(ok=True))
        assert record.root_hex == merkle_root([e_z1.event_hash, e_a1.event_hash, e_z2.event_hash])
        # a (stream_id, seq) order groups both ZZ events together -> different root
        assert record.root_hex != merkle_root([e_a1.event_hash, e_z1.event_hash, e_z2.event_hash])
        assert record.head_hash == e_z2.event_hash

    def test_empty_table_raises_value_error(self, db):
        EvidenceEvent.query.delete()
        db.session.commit()
        with pytest.raises(ValueError, match="no evidence events to anchor"):
            build_batch(NullAnchorProvider(ok=True))

    def test_dirty_event_hash_recorded_as_pending_not_raised(self, db):
        """E-1: an un-hexable event_hash degrades to a PENDING record with an error,
        instead of crashing with TypeError / binascii.Error."""
        stream_id = _stream_id("anchor-dirty")
        event = append_event(stream_id, "EVT", {"i": 1})
        original_hash = event.event_hash
        event.event_hash = "zz" * 32
        db.session.commit()

        record = build_batch(NullAnchorProvider(ok=True))
        assert record.status == "PENDING"
        assert record.root_hex is None
        assert record.event_count is None and record.head_hash is None
        assert "invalid event hash" in record.error

        # leave the shared table clean for later batch tests
        event.event_hash = original_hash
        db.session.commit()

    def test_provider_exception_is_recorded(self, db):
        stream_id = _stream_id("anchor-boom")
        append_event(stream_id, "EVT", {"i": 1})

        class BoomProvider(AnchorProvider):
            name = "boom"

            def submit(self, root_hex):
                raise RuntimeError("boom")

        record = build_batch(BoomProvider())
        assert record.status == "PENDING"
        assert record.proof_path is None
        assert "boom" in record.error

    def test_overlong_provider_error_truncated_to_255(self, db):
        """E-2: providers can return arbitrarily long errors; the column is VARCHAR(255)."""
        stream_id = _stream_id("anchor-longerr")
        append_event(stream_id, "EVT", {"i": 1})

        class LongErrorProvider(AnchorProvider):
            name = "longerr"

            def submit(self, root_hex):
                return {"status": "PENDING", "proof_bytes": None, "error": "x" * 400}

        record = build_batch(LongErrorProvider())
        assert record.status == "PENDING"
        assert len(record.error) == 255

    def test_proof_write_failure_recorded(self, db, tmp_path, monkeypatch):
        """E-3 failure path: an unwritable ANCHOR_DIR keeps the root but no proof."""
        stream_id = _stream_id("anchor-nodisk")
        append_event(stream_id, "EVT", {"i": 1})
        blocker = tmp_path / "blocker"
        blocker.write_text("this is a file, not a directory")
        monkeypatch.setattr("evidence.anchor.ANCHOR_DIR", str(blocker / "anchors"))

        record = build_batch(NullAnchorProvider(ok=True))
        assert record.status == "PENDING"
        assert record.root_hex and len(record.root_hex) == 64
        assert "proof write failed" in record.error
        assert record.proof_path is None
        assert record.proof_sha256 is None

    def test_proof_file_written_atomically_with_no_leftover_tmp(self, db, tmp_path, monkeypatch):
        stream_id = _stream_id("anchor-atomic")
        append_event(stream_id, "EVT", {"i": 1})
        monkeypatch.setattr("evidence.anchor.ANCHOR_DIR", str(tmp_path / "anchors"))

        record = build_batch(NullAnchorProvider(ok=True))
        assert record.status == "SUBMITTED"
        assert os.listdir(tmp_path / "anchors") == [f"{record.batch_id}.ots"]

    def test_root_matches_manual_merkle_over_all_events(self, db):
        stream_id = _stream_id("anchor-manual")
        append_event(stream_id, "EVT", {"x": 1})
        record = build_batch(NullAnchorProvider(ok=True))

        events = EvidenceEvent.query.order_by(EvidenceEvent.id.asc()).all()
        assert record.root_hex == merkle_root([event.event_hash for event in events])

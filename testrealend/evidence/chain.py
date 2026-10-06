"""Hash-chained evidence stream: append and full verification.

Chain layout per event:
  prev_hash  = previous event's event_hash (64 hex chars); first event = 64 zeros
  event_hash = sha256(DOMAIN_EVENT || prev_hash_bytes || canonical-CBOR event body)
  signature  = Ed25519 over the 32 RAW BYTES of event_hash

The signature deliberately signs the chain NODE (the event_hash digest), not
the event body itself: the digest already commits to prev_hash + body, so the
signature anchors both content and position in the stream.

The body binds stream id and sequence number, so identical genesis content
written to two different streams within the same second still yields distinct
event_hash values (no UNIQUE(event_hash) collision).
"""

import hashlib
import io
from datetime import UTC, datetime

import cbor2
from cryptography.hazmat.primitives import serialization

from crypto import canonical
from crypto.keys import ensure_active_key, get_public_key_by_kid
from evidence.constants import DOMAIN_EVENT
from extension.extension import db
from model.evidence_event import EvidenceEvent

GENESIS_HASH = "0" * 64


def _strict_loads(data: bytes):
    """Decode exactly one CBOR item, rejecting trailing bytes (B-5).

    Same idea as the strict decode in ``crypto.cose``: a payload_cbor column
    with appended garbage must fail verification instead of being silently
    accepted by a trailing-byte-tolerant decoder.
    """
    stream = io.BytesIO(data)
    obj = cbor2.CBORDecoder(stream).decode()
    if stream.read(1):
        raise ValueError("trailing bytes after CBOR event body")
    return obj


def _epoch(ts: datetime) -> int:
    """Epoch seconds for the signed body; naive datetimes are treated as UTC.

    The epoch is second-resolution: sub-second components of ``ts`` are NOT
    committed to the hash (two events differing only in microseconds hash
    identically with respect to ts).
    """
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return int(ts.timestamp())


def _raw_public_bytes(public_key) -> bytes:
    return public_key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)


def _assert_kid_matches_signing_key(kid: int, private_key) -> None:
    """Reject an explicit kid whose registered public key is not the signer's.

    Unknown kids and key mismatches both raise ValueError *before* any row is
    written, so a mis-stamped event can never reach the table.
    """
    try:
        registered = get_public_key_by_kid(kid)
    except KeyError as e:
        raise ValueError(f"unknown kid: {kid}") from e
    if _raw_public_bytes(registered) != _raw_public_bytes(private_key.public_key()):
        raise ValueError(f"kid {kid} does not match the signing key")


def _event_body(stream_id: str, seq: int, event_type: str, payload: dict, epoch: int) -> bytes:
    """Canonical event body committed to by event_hash — single source of truth for append/verify."""
    return canonical.dumps({"stream": stream_id, "seq": seq, "type": event_type, "payload": payload, "ts": epoch})


def append_event(stream_id: str, event_type: str, payload: dict, kid=None, ts=None) -> EvidenceEvent:
    """Append one event to the stream (first seq=1) and return the stored row.

    Single-writer assumption: ``seq`` is computed as MAX(seq)+1 with no
    concurrency protection. Two racing writers on one stream make the loser hit
    the UNIQUE(stream_id, seq) constraint and fail closed (no row stored).

    An explicit ``kid`` must name a registered key whose public half matches
    the signing key; anywhere else ValueError is raised before any write.

    ``ts`` is normalised to naive UTC (tz-aware input is converted, naive input
    is interpreted as UTC and kept naive) so that the stored column always
    equals the value committed to by event_hash. Only second resolution is
    committed (see ``_epoch``).
    """
    active_kid, private_key = ensure_active_key()
    if kid is None:
        kid = active_kid
    else:
        _assert_kid_matches_signing_key(kid, private_key)
    if ts is None:
        ts = datetime.now(UTC)
    if ts.tzinfo is not None:
        ts = ts.astimezone(UTC).replace(tzinfo=None)

    last = EvidenceEvent.query.filter_by(stream_id=stream_id).order_by(EvidenceEvent.seq.desc()).first()
    seq = last.seq + 1 if last is not None else 1
    prev_hash = last.event_hash if last is not None else GENESIS_HASH

    event_bytes = _event_body(stream_id, seq, event_type, payload, _epoch(ts))
    event_hash = hashlib.sha256(DOMAIN_EVENT + bytes.fromhex(prev_hash) + event_bytes).hexdigest()
    signature = private_key.sign(bytes.fromhex(event_hash))

    event = EvidenceEvent(
        stream_id=stream_id,
        seq=seq,
        event_type=event_type,
        payload_cbor=event_bytes,
        prev_hash=prev_hash,
        event_hash=event_hash,
        signature=signature,
        kid=kid,
        ts=ts,
    )
    db.session.add(event)
    db.session.commit()
    return event


def get_events(stream_id: str) -> list[EvidenceEvent]:
    """All events of a stream in ascending seq order."""
    return EvidenceEvent.query.filter_by(stream_id=stream_id).order_by(EvidenceEvent.seq.asc()).all()


def _broken(length: int, broken_at: int, reason: str) -> dict:
    return {"valid": False, "length": length, "head_hash": None, "broken_at": broken_at, "reason": reason}


def verify_stream(stream_id: str) -> dict:
    """Recompute the whole chain and verify every signature.

    The event body is re-derived field-by-field from the stored row (payload is
    re-parsed from payload_cbor; ts is normalised back to epoch seconds), so
    tampering with any stored field or the CBOR body is detected.

    Returns ``{"valid", "length", "head_hash", "broken_at", "reason"}`` where
    ``broken_at`` is the 1-based position (== seq for healthy prefixes) of the
    first broken event, or None when the stream is valid.

    ``valid`` is NOT ``complete``: it only proves the events currently in the
    table are self-consistent. It cannot detect truncation of trailing events.
    Completeness must be checked against an anchor record's ``event_count`` /
    ``head_hash`` (or the stream's own head against an anchored head).
    """
    events = get_events(stream_id)
    prev_hash = GENESIS_HASH
    expected_seq = 1
    for position, event in enumerate(events, start=1):
        if event.seq != expected_seq:
            return _broken(len(events), position, f"seq gap: expected {expected_seq}, got {event.seq}")
        if event.prev_hash != prev_hash:
            return _broken(len(events), position, "prev_hash does not match previous event_hash")
        try:
            stored_body = _strict_loads(bytes(event.payload_cbor))
            recomputed = hashlib.sha256(
                DOMAIN_EVENT
                + bytes.fromhex(event.prev_hash)
                + _event_body(event.stream_id, event.seq, event.event_type, stored_body["payload"], _epoch(event.ts))
            ).hexdigest()
        except Exception as e:
            return _broken(len(events), position, f"event body re-derivation failed: {e}")
        if recomputed != event.event_hash:
            return _broken(len(events), position, "event_hash mismatch (payload tampered?)")
        try:
            public_key = get_public_key_by_kid(event.kid)
            public_key.verify(bytes(event.signature), bytes.fromhex(event.event_hash))
        except KeyError as e:
            return _broken(len(events), position, str(e))
        except Exception as e:  # cryptography.exceptions.InvalidSignature and friends
            return _broken(len(events), position, f"signature invalid: {e}")
        prev_hash = event.event_hash
        expected_seq += 1

    head_hash = events[-1].event_hash if events else None
    return {"valid": True, "length": len(events), "head_hash": head_hash, "broken_at": None, "reason": None}

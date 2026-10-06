"""Hash-chained evidence stream: append and full verification.

Chain layout per event:
  prev_hash  = previous event's event_hash (64 hex chars); first event = 64 zeros
  event_hash = sha256(DOMAIN_EVENT || prev_hash_bytes || canonical-CBOR event body)
  signature  = Ed25519 over the 32 RAW BYTES of event_hash

The signature deliberately signs the chain NODE (the event_hash digest), not
the event body itself: the digest already commits to prev_hash + body, so the
signature anchors both content and position in the stream.
"""

import hashlib
from datetime import UTC, datetime

from crypto import canonical
from crypto.keys import ensure_active_key, get_public_key_by_kid
from evidence.constants import DOMAIN_EVENT
from extension.extension import db
from model.evidence_event import EvidenceEvent

GENESIS_HASH = "0" * 64


def _epoch(ts: datetime) -> int:
    """Epoch seconds for the signed body; naive datetimes are treated as UTC."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return int(ts.timestamp())


def append_event(stream_id: str, event_type: str, payload: dict, kid=None, ts=None) -> EvidenceEvent:
    """Append one event to the stream (first seq=1) and return the stored row."""
    active_kid, private_key = ensure_active_key()
    if kid is None:
        kid = active_kid
    if ts is None:
        ts = datetime.now(UTC)

    last = EvidenceEvent.query.filter_by(stream_id=stream_id).order_by(EvidenceEvent.seq.desc()).first()
    seq = last.seq + 1 if last is not None else 1
    prev_hash = last.event_hash if last is not None else GENESIS_HASH

    event_bytes = canonical.dumps({"type": event_type, "payload": payload, "ts": _epoch(ts)})
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

    Returns ``{"valid", "length", "head_hash", "broken_at", "reason"}`` where
    ``broken_at`` is the 1-based position (== seq for healthy prefixes) of the
    first broken event, or None when the stream is valid.
    """
    events = get_events(stream_id)
    prev_hash = GENESIS_HASH
    expected_seq = 1
    for position, event in enumerate(events, start=1):
        if event.seq != expected_seq:
            return _broken(len(events), position, f"seq gap: expected {expected_seq}, got {event.seq}")
        if event.prev_hash != prev_hash:
            return _broken(len(events), position, "prev_hash does not match previous event_hash")
        recomputed = hashlib.sha256(
            DOMAIN_EVENT + bytes.fromhex(event.prev_hash) + bytes(event.payload_cbor)
        ).hexdigest()
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

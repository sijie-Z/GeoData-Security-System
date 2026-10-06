"""Batch anchoring: merkle root over all evidence events -> anchor provider.

P1 batch semantics: a batch is a SNAPSHOT of every EvidenceEvent as of "now",
sorted by (stream_id, seq) — replaying it later produces the same root as long
as no new events have arrived. Incremental (delta) batches are deferred.
"""

import os
import uuid
from datetime import UTC, datetime

import httpx

from config import BASE_DIR
from evidence.merkle import merkle_root
from extension.extension import db
from model.anchor_record import AnchorRecord
from model.evidence_event import EvidenceEvent

ANCHOR_DIR = os.path.join(BASE_DIR, "instance", "anchors")


class AnchorProvider:
    """Interface: submit a merkle root (hex) to an external timestamping service."""

    name = "base"

    def submit(self, root_hex: str) -> dict:
        raise NotImplementedError


class OpenTimestampsProvider(AnchorProvider):
    """OpenTimestamps calendar-pool client. Network failures never propagate."""

    name = "opentimestamps"
    url = "https://a.pool.opentimestamps.org/digest"

    def submit(self, root_hex: str) -> dict:
        try:
            response = httpx.post(self.url, content=bytes.fromhex(root_hex), timeout=5)
            response.raise_for_status()
            return {"status": "SUBMITTED", "proof_bytes": response.content, "error": None}
        except Exception as e:
            return {"status": "PENDING", "proof_bytes": None, "error": str(e)}


class NullAnchorProvider(AnchorProvider):
    """In-memory provider for tests: ok=True always succeeds, ok=False always fails."""

    name = "null"

    def __init__(self, ok: bool = True):
        self.ok = ok

    def submit(self, root_hex: str) -> dict:
        if self.ok:
            return {"status": "SUBMITTED", "proof_bytes": b"NULL-ANCHOR:" + bytes.fromhex(root_hex), "error": None}
        return {"status": "PENDING", "proof_bytes": None, "error": "null provider configured to fail"}


def build_batch(provider=None) -> AnchorRecord:
    """Anchor all evidence events as one batch. Never raises on network failure.

    Raises ValueError when there is nothing to anchor (empty event table).
    """
    if provider is None:
        provider = OpenTimestampsProvider()

    events = EvidenceEvent.query.order_by(EvidenceEvent.stream_id.asc(), EvidenceEvent.seq.asc()).all()
    root_hex = merkle_root([event.event_hash for event in events])
    if root_hex is None:
        raise ValueError("no evidence events to anchor")

    batch_id = str(uuid.uuid4())
    record = AnchorRecord(batch_id=batch_id, root_hex=root_hex, provider=provider.name, status="PENDING")
    db.session.add(record)
    db.session.commit()

    try:
        result = provider.submit(root_hex)
    except Exception as e:  # defensive: stay true to "never raise" even for custom providers
        result = {"status": "PENDING", "proof_bytes": None, "error": str(e)}

    proof_bytes = result.get("proof_bytes")
    if result.get("status") == "SUBMITTED" and proof_bytes:
        try:
            os.makedirs(ANCHOR_DIR, exist_ok=True)
            proof_path = os.path.join(ANCHOR_DIR, f"{batch_id}.ots")
            with open(proof_path, "wb") as fh:
                fh.write(proof_bytes)
            record.status = "SUBMITTED"
            record.proof_path = proof_path
        except OSError as e:
            record.status = "PENDING"
            record.error = f"proof write failed: {e}"
    else:
        record.status = "PENDING"
        record.error = result.get("error") or "provider did not return a proof"
    record.updated_at = datetime.now(UTC)
    db.session.commit()
    return record

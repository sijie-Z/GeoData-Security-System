"""Batch anchoring: merkle root over all evidence events -> anchor provider.

P1 batch semantics: a batch is a SNAPSHOT of every EvidenceEvent as of "now",
ordered by the autoincrement ``id`` (insertion order). ``id`` ordering is
deterministic on both MySQL and SQLite and independent of the database's text
collation, so replaying a batch without new events produces the same root on
every backend. Incremental (delta) batches are deferred.
"""

import hashlib
import json
import os
import tempfile
import uuid
from datetime import UTC, datetime

import httpx

from config import BASE_DIR, Config
from evidence.merkle import merkle_root
from extension.extension import db
from model.anchor_record import AnchorRecord
from model.evidence_event import EvidenceEvent

try:  # web3 is optional at import time — the app must boot (EVM disabled) without it
    from web3 import Web3
except Exception:  # pragma: no cover - only on installs without web3
    Web3 = None

ANCHOR_DIR = os.path.join(BASE_DIR, "instance", "anchors")

# Minimal ABI for contracts/AnchorRegistry.sol (keep in sync with the Solidity source).
EVM_ANCHOR_ABI = [
    {
        "type": "function",
        "name": "anchor",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "root", "type": "bytes32"}],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "exists",
        "stateMutability": "view",
        "inputs": [{"name": "root", "type": "bytes32"}],
        "outputs": [{"name": "", "type": "bool"}],
    },
    {
        "type": "function",
        "name": "getTimestamp",
        "stateMutability": "view",
        "inputs": [{"name": "root", "type": "bytes32"}],
        "outputs": [{"name": "", "type": "uint64"}],
    },
    {
        "type": "event",
        "name": "Anchored",
        "anonymous": False,
        "inputs": [
            {"name": "root", "type": "bytes32", "indexed": True},
            {"name": "timestamp", "type": "uint64", "indexed": False},
            {"name": "sender", "type": "address", "indexed": True},
        ],
    },
    {"type": "error", "name": "AlreadyAnchored", "inputs": []},
]

EVM_PENDING_ERROR = "EVM provider not configured"


def _hex32_bytes(value) -> bytes:
    """Parse a 0x-optional hex string into exactly 32 bytes (bytes32)."""
    text = str(value).strip()
    if text.startswith(("0x", "0X")):
        text = text[2:]
    raw = bytes.fromhex(text)
    if len(raw) != 32:
        raise ValueError(f"root must be 32 bytes, got {len(raw)}")
    return raw


def _hex0x(value) -> str:
    """Normalize a web3 hex value (tx hash / event bytes32) to 0x-prefixed hex."""
    text = value.hex() if hasattr(value, "hex") else str(value)
    return text if text.startswith("0x") else f"0x{text}"


def _truncate_error(text) -> str:
    """AnchorRecord.error is VARCHAR(255); MySQL strict mode rejects longer values."""
    return str(text)[:255]


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
            # Tight connect timeout: a DNS/connect stall must not pin a worker.
            response = httpx.post(self.url, content=bytes.fromhex(root_hex), timeout=httpx.Timeout(5.0, connect=2.0))
            response.raise_for_status()
            return {"status": "SUBMITTED", "proof_bytes": response.content, "error": None}
        except Exception as e:
            return {"status": "PENDING", "proof_bytes": None, "error": str(e)}


class EVMAnchorProvider(AnchorProvider):
    """EVM (Sepolia) anchor provider: AnchorRegistry.anchor(bytes32) via web3.py.

    Never raises: configuration gaps and RPC/node errors all degrade to
    ``{"status": "PENDING", "error": ...}`` (same discipline as OpenTimestamps).
    The private key is read from the git-ignored key file (see ``evidence/evm.py``)
    and is never logged nor returned. ``w3``/``contract`` are injectable so tests
    run against an in-memory eth-tester chain. Supports the honest claim "this
    root existed before this moment" only — on-chain timestamping, no notary.
    """

    name = "evm-sepolia"

    def __init__(self, rpc_url=None, chain_id=None, contract_address=None, private_key=None, w3=None, contract=None):
        self.rpc_url = rpc_url or Config.EVM_RPC_URL
        try:
            self.chain_id = int(chain_id if chain_id is not None else Config.EVM_CHAIN_ID)
        except (TypeError, ValueError):
            self.chain_id = None
        self.contract = contract
        self.address = None
        injected = w3 is not None

        if injected:
            self.w3 = w3
        elif Web3 is not None:
            try:
                from web3.providers.rpc import HTTPProvider

                self.w3 = Web3(HTTPProvider(self.rpc_url, request_kwargs={"timeout": 8}))
            except Exception:
                self.w3 = None
        else:
            self.w3 = None

        if private_key is None and not injected:
            # Only the default HTTP setup falls back to the key file: an injected w3
            # is the test hook (in-memory tester chains expose unlocked accounts).
            try:
                from evidence.evm import load_private_key

                private_key = load_private_key()
            except Exception:
                private_key = None

        if private_key and self.w3 is not None:
            try:
                from eth_account import Account
                from web3.middleware import SignAndSendRawMiddlewareBuilder

                account = Account.from_key(private_key)
                self.address = Web3.to_checksum_address(account.address)
                # Sign + send raw locally (needed on a real network). Only added for
                # key-based setups: an injected tester w3 already has unlocked accounts.
                self.w3.middleware_onion.add(SignAndSendRawMiddlewareBuilder.build(account))
                self.w3.eth.default_account = self.address
            except Exception:
                self.address = None
        elif injected:
            # In-memory tester chains expose unlocked accounts; a remote HTTP node
            # never does, so this lookup only runs for injected w3 (no network I/O).
            try:
                accounts = self.w3.eth.accounts
                if accounts:
                    self.address = Web3.to_checksum_address(accounts[0])
            except Exception:
                self.address = None

        if self.contract is None:
            address = contract_address or Config.EVM_CONTRACT_ADDRESS
            if address and self.w3 is not None:
                try:
                    self.contract = self.w3.eth.contract(address=Web3.to_checksum_address(address), abi=EVM_ANCHOR_ABI)
                except Exception:
                    self.contract = None

    def _can_submit(self) -> bool:
        if str(Config.EVM_ANCHOR_ENABLED).strip().lower() in {"0", "false", "off", "no", "disabled"}:
            return False
        return self.w3 is not None and self.contract is not None and self.address is not None

    def _can_verify(self) -> bool:
        # Verification is read-only: it needs a chain + contract, not a key.
        return self.w3 is not None and self.contract is not None

    def submit(self, root_hex: str) -> dict:
        """Anchor a merkle root; SUBMITTED with the tx hash as anchor_id, else PENDING."""
        try:
            if not self._can_submit():
                return {"status": "PENDING", "proof_bytes": None, "error": EVM_PENDING_ERROR}
            root = _hex32_bytes(root_hex)
            tx_hash = self.contract.functions.anchor(root).transact({"from": self.address})
            tx_hex = _hex0x(tx_hash)
            meta = {
                "scheme": self.name,
                "tx_hash": tx_hex,
                "chain_id": self.chain_id,
                "contract": self.contract.address,
                "sender": self.address,
                "rpc": self.rpc_url,
                "root_hex": root.hex(),
            }
            receipt = None
            try:
                # eth-tester mines instantly; on a real chain this may time out and
                # verify() picks the block up later — either way the tx is in flight.
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=12)
            except Exception:
                receipt = None
            if receipt is not None:
                if int(receipt.get("status", 1)) != 1:
                    return {"status": "PENDING", "proof_bytes": None, "error": "anchor transaction reverted"}
                meta["block_number"] = receipt["blockNumber"]
                try:
                    meta["block_timestamp"] = self.w3.eth.get_block(receipt["blockNumber"])["timestamp"]
                except Exception:
                    pass
            return {"status": "SUBMITTED", "anchor_id": tx_hex, "proof_bytes": None, "proof_meta": meta, "error": None}
        except Exception as e:
            return {"status": "PENDING", "proof_bytes": None, "error": _truncate_error(e)}

    def verify(self, anchor_id: str) -> dict:
        """Receipt + on-chain getTimestamp check; PENDING (never raises) on any gap."""
        try:
            if not self._can_verify():
                return {"status": "PENDING", "proof": None, "error": EVM_PENDING_ERROR}
            tx_hex = str(anchor_id).strip()
            if not tx_hex.startswith("0x"):
                tx_hex = f"0x{tx_hex}"
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hex)
            except Exception as e:
                return {"status": "PENDING", "proof": None, "error": _truncate_error(e)}
            if receipt is None:
                return {"status": "PENDING", "proof": None, "error": "no receipt yet"}
            if int(receipt.get("status", 1)) != 1:
                return {"status": "PENDING", "proof": None, "error": "anchor transaction not successful"}

            root_hex = None
            try:
                events = self.contract.events.Anchored().process_receipt(receipt)
                if events:
                    root_hex = _hex0x(events[0]["args"]["root"])
            except Exception:
                root_hex = None
            onchain_timestamp = None
            if root_hex:
                try:
                    onchain_timestamp = int(self.contract.functions.getTimestamp(_hex32_bytes(root_hex)).call())
                except Exception:
                    onchain_timestamp = None

            block = self.w3.eth.get_block(receipt["blockNumber"])
            latest = int(self.w3.eth.block_number)
            proof = {
                "tx_hash": tx_hex,
                "block_number": receipt["blockNumber"],
                "block_timestamp": block["timestamp"],
                "confirmed": (latest - int(receipt["blockNumber"])) > 12,
                "contract": self.contract.address,
                "root_hex": root_hex,
                "onchain_timestamp": onchain_timestamp,
            }
            return {"status": "PROOF_READY", "proof": proof, "error": None}
        except Exception as e:
            return {"status": "PENDING", "proof": None, "error": _truncate_error(e)}


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
    """Anchor all evidence events as one batch. Never raises on provider, merkle or I/O failure.

    The batch is ordered by ``EvidenceEvent.id`` (insertion order — see module
    docstring) and records ``event_count``/``head_hash`` alongside the root, so
    a later verifier can check completeness, not just self-consistency.

    Provider results carry a proof either as raw bytes (OpenTimestamps ``.ots``)
    or as a ``proof_meta`` dict (EVM: written as a JSON evidence pack holding
    tx_hash/chain_id/contract/block/timestamp/rpc). Both land in
    ``proof_path`` + ``proof_sha256``; the transient ``proof_meta`` attribute is
    kept on the returned record for the API layer (no new columns).

    Raises ValueError when there is nothing to anchor (empty event table).
    """
    if provider is None:
        provider = OpenTimestampsProvider()

    events = EvidenceEvent.query.order_by(EvidenceEvent.id.asc()).all()
    if not events:
        raise ValueError("no evidence events to anchor")

    batch_id = str(uuid.uuid4())
    try:
        root_hex = merkle_root([event.event_hash for event in events])
    except ValueError as e:
        # E-1: a dirty event_hash row must degrade to a recorded error, not a 500.
        record = AnchorRecord(
            batch_id=batch_id,
            root_hex=None,
            provider=provider.name,
            status="PENDING",
            error=_truncate_error(f"merkle root failed: {e}"),
            updated_at=datetime.now(UTC),
        )
        db.session.add(record)
        db.session.commit()
        return record

    record = AnchorRecord(
        batch_id=batch_id,
        root_hex=root_hex,
        provider=provider.name,
        status="PENDING",
        event_count=len(events),
        head_hash=events[-1].event_hash,
    )
    db.session.add(record)
    db.session.commit()

    try:
        result = provider.submit(root_hex)
    except Exception as e:  # defensive: stay true to "never raise" even for custom providers
        result = {"status": "PENDING", "proof_bytes": None, "error": str(e)}

    proof_bytes = result.get("proof_bytes")
    proof_meta = result.get("proof_meta")
    # Transient (non-column) copy for the API layer, e.g. EVM explorer URLs.
    record.proof_meta = proof_meta if isinstance(proof_meta, dict) else None
    if result.get("status") == "SUBMITTED" and (proof_bytes or proof_meta):
        try:
            os.makedirs(ANCHOR_DIR, exist_ok=True)
            if proof_bytes:
                proof_path = os.path.join(ANCHOR_DIR, f"{batch_id}.ots")
                payload = proof_bytes
            else:
                # EVM evidence pack: everything a verifier needs to reproduce the
                # on-chain lookup (tx / chain / contract / block / timestamp / rpc).
                proof_path = os.path.join(ANCHOR_DIR, f"{batch_id}.evm.json")
                pack = {"batch_id": batch_id, "provider": provider.name, **proof_meta}
                payload = json.dumps(pack, sort_keys=True, indent=2).encode("utf-8")
            # E-3: atomic write — write to a tempfile in the same directory, then
            # os.replace so a crashed write can never leave a partial proof file.
            fd, tmp_path = tempfile.mkstemp(prefix=f".{batch_id}-", suffix=".tmp", dir=ANCHOR_DIR)
            try:
                with os.fdopen(fd, "wb") as fh:
                    fh.write(payload)
                os.replace(tmp_path, proof_path)
            except OSError:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
            record.status = "SUBMITTED"
            record.proof_path = proof_path
            record.proof_sha256 = hashlib.sha256(payload).hexdigest()
        except OSError as e:
            record.status = "PENDING"
            record.error = _truncate_error(f"proof write failed: {e}")
    else:
        record.status = "PENDING"
        record.error = _truncate_error(result.get("error") or "provider did not return a proof")
    record.updated_at = datetime.now(UTC)
    db.session.commit()
    return record

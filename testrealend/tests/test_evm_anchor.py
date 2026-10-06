"""EVM anchor tests: in-memory eth-tester chain only — no network, no Sepolia.

Covers (taskbook Step 4): provider state machine (submit -> SUBMITTED tx hash,
receipt status, getTimestamp == block time; verify -> PROOF_READY; duplicate
root -> AlreadyAnchored captured as PENDING, never raised), unconfigured
degradation, the full build_batch EVM chain (provider tag, JSON evidence pack,
proof_sha256, merkle re-check) and the anchor/build endpoint contract for
{"provider": "evm"} (explorer_url when configured, 200 + PENDING otherwise).

CI note: eth-tester/solcx are import-skipped when unavailable; the contract is
compiled with a cached solc 0.8.24 (first run downloads it via py-solc-x).
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

pytest.importorskip("web3")
pytest.importorskip("eth_tester")
solcx = pytest.importorskip("solcx")

from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

import evidence.anchor as anchor_mod
from evidence.anchor import EVM_PENDING_ERROR, EVMAnchorProvider
from evidence.merkle import merkle_root
from model.evidence_event import EvidenceEvent

CONTRACT_SOURCE = Path(__file__).resolve().parents[2] / "contracts" / "AnchorRegistry.sol"
SOLC_VERSION = "0.8.24"

try:
    if str(SOLC_VERSION) not in {str(v) for v in solcx.get_installed_solc_versions()}:
        solcx.install_solc(SOLC_VERSION)
    _compiled = solcx.compile_source(
        CONTRACT_SOURCE.read_text(encoding="utf-8"), output_values=["abi", "bin"], solc_version=SOLC_VERSION
    )
    _ANCHOR_REGISTRY = _compiled[next(k for k in _compiled if k.endswith(":AnchorRegistry"))]
except Exception as exc:  # pragma: no cover - offline runner without a cached solc
    pytest.skip(f"solc {SOLC_VERSION} unavailable: {exc}", allow_module_level=True)


def _seed_events(db, count=3, prefix="evm-event"):
    """Insert `count` hash-chained evidence rows; returns the hashes in id order."""
    EvidenceEvent.query.delete()
    db.session.commit()
    hashes = [hashlib.sha256(f"{prefix}-{i}".encode()).hexdigest() for i in range(count)]
    for i, event_hash in enumerate(hashes):
        db.session.add(
            EvidenceEvent(
                stream_id=f"{prefix}-stream",
                seq=i + 1,
                event_type="TestEvent",
                payload_cbor=b"\xa0",
                prev_hash=None,
                event_hash=event_hash,
                signature=None,
                kid=1,
                ts=datetime.now(UTC),
            )
        )
    db.session.commit()
    return hashes


@pytest.fixture(scope="module")
def tester_w3():
    return Web3(EthereumTesterProvider())


@pytest.fixture()
def evm_chain(tester_w3):
    """Deploy a fresh AnchorRegistry per test on the shared in-memory chain."""
    sender = tester_w3.eth.accounts[0]
    factory = tester_w3.eth.contract(abi=_ANCHOR_REGISTRY["abi"], bytecode=_ANCHOR_REGISTRY["bin"])
    receipt = tester_w3.eth.wait_for_transaction_receipt(factory.constructor().transact({"from": sender}))
    contract = tester_w3.eth.contract(address=receipt.contractAddress, abi=_ANCHOR_REGISTRY["abi"])
    return tester_w3, contract


class TestProviderStateMachine:
    def test_submit_verify_duplicate_and_confirmation(self, evm_chain):
        w3, contract = evm_chain
        provider = EVMAnchorProvider(w3=w3, contract=contract)
        root = hashlib.sha256(b"evm-anchor-state-machine").hexdigest()

        result = provider.submit(root)
        assert result["status"] == "SUBMITTED", result.get("error")
        assert result["proof_bytes"] is None
        assert result["error"] is None
        anchor_id = result["anchor_id"]
        assert anchor_id.startswith("0x") and len(anchor_id) == 66

        # the tx really landed on-chain and getTimestamp equals the block time
        receipt = w3.eth.get_transaction_receipt(anchor_id)
        assert receipt["status"] == 1
        block = w3.eth.get_block(receipt["blockNumber"])
        assert contract.functions.getTimestamp(bytes.fromhex(root)).call() == block["timestamp"]
        assert contract.functions.exists(bytes.fromhex(root)).call() is True

        # proof_meta: the evidence pack data, no key material anywhere
        meta = result["proof_meta"]
        assert meta["tx_hash"] == anchor_id
        assert meta["contract"] == contract.address
        assert meta["root_hex"] == root
        assert meta["block_number"] == receipt["blockNumber"]
        assert meta["block_timestamp"] == block["timestamp"]
        assert meta["sender"] == provider.address

        verified = provider.verify(anchor_id)
        assert verified["status"] == "PROOF_READY"
        proof = verified["proof"]
        assert proof["tx_hash"] == anchor_id
        assert proof["block_number"] == receipt["blockNumber"]
        assert proof["block_timestamp"] == block["timestamp"]
        assert proof["confirmed"] is False  # fresh tx: depth well under 12 blocks
        assert proof["contract"] == contract.address
        assert proof["root_hex"].lower() == f"0x{root}"
        assert proof["onchain_timestamp"] == block["timestamp"]

        # mine past the confirmation window -> confirmed flips to True
        ethereum_tester = w3.provider.ethereum_tester
        for _ in range(13):
            ethereum_tester.mine_block()
        reverified = provider.verify(anchor_id)
        assert reverified["status"] == "PROOF_READY"
        assert reverified["proof"]["confirmed"] is True

        # duplicate anchor of the same root: AlreadyAnchored revert captured as
        # PENDING + error (custom-error selector in eth-tester), never raised
        duplicate = provider.submit(root)
        assert duplicate["status"] == "PENDING"
        assert duplicate["proof_bytes"] is None
        assert duplicate["error"] and "revert" in duplicate["error"].lower()

    def test_verify_unknown_tx_is_pending(self, evm_chain):
        w3, contract = evm_chain
        provider = EVMAnchorProvider(w3=w3, contract=contract)
        result = provider.verify("0x" + "00" * 32)
        assert result["status"] == "PENDING"
        assert result["proof"] is None
        assert result["error"]

    def test_unconfigured_provider_degrades_to_pending(self, tester_w3):
        # no contract address configured -> submit/verify stay PENDING, never raise
        provider = EVMAnchorProvider(w3=tester_w3)
        result = provider.submit("ab" * 32)
        assert result == {"status": "PENDING", "proof_bytes": None, "error": EVM_PENDING_ERROR}
        verified = provider.verify("0x" + "ab" * 32)
        assert verified["status"] == "PENDING"
        assert verified["proof"] is None
        assert verified["error"] == EVM_PENDING_ERROR


class TestBuildBatchEVM:
    def test_build_batch_writes_json_pack_and_tags_provider(self, db, evm_chain, tmp_path, monkeypatch):
        w3, contract = evm_chain
        monkeypatch.setattr(anchor_mod, "ANCHOR_DIR", str(tmp_path / "anchors"))
        hashes = _seed_events(db, count=3)

        provider = EVMAnchorProvider(w3=w3, contract=contract)
        record = anchor_mod.build_batch(provider=provider)

        assert record.provider == "evm-sepolia"
        assert record.status == "SUBMITTED", record.error
        assert record.root_hex == merkle_root(hashes)  # merkle re-computation matches
        assert record.event_count == 3

        pack_path = Path(record.proof_path)
        assert pack_path.exists() and pack_path.name.endswith(".evm.json")
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        assert pack["batch_id"] == record.batch_id
        assert pack["provider"] == "evm-sepolia"
        assert pack["root_hex"] == record.root_hex
        assert len(pack["tx_hash"]) == 66
        assert pack["contract"] == contract.address
        assert {"tx_hash", "chain_id", "contract", "block_number", "block_timestamp", "rpc"} <= set(pack)
        # proof_sha256 covers the exact bytes of the written pack
        assert record.proof_sha256 == hashlib.sha256(pack_path.read_bytes()).hexdigest()
        # transient meta (API layer) mirrors the pack; no key material in it
        assert record.proof_meta["tx_hash"] == pack["tx_hash"]

        # the packed tx hash really exists on the chain and anchored this root
        receipt = w3.eth.get_transaction_receipt(pack["tx_hash"])
        assert receipt["status"] == 1
        assert contract.functions.exists(bytes.fromhex(record.root_hex)).call() is True


class TestAnchorBuildEndpointEVM:
    def test_evm_provider_returns_explorer_url(self, db, client, auth_headers, evm_chain, tmp_path, monkeypatch):
        w3, contract = evm_chain
        monkeypatch.setattr(anchor_mod, "ANCHOR_DIR", str(tmp_path / "anchors"))
        monkeypatch.setattr(
            "resource.forensics_resource.EVMAnchorProvider",
            lambda *a, **k: anchor_mod.EVMAnchorProvider(w3=w3, contract=contract),
        )
        _seed_events(db, count=2, prefix="evm-endpoint")

        resp = client.post("/api/forensics/anchor/build", json={"provider": "evm"}, headers=auth_headers)
        assert resp.status_code == 200, resp.get_json()
        batch = resp.get_json()["batch"]
        assert batch["provider"] == "evm-sepolia"
        assert batch["status"] == "SUBMITTED"
        assert batch["explorer_url"] is not None
        assert batch["explorer_url"].startswith("https://sepolia.etherscan.io/tx/0x")
        tx_hex = batch["explorer_url"].rsplit("/", 1)[1]
        assert w3.eth.get_transaction_receipt(tx_hex)["status"] == 1

    def test_evm_unconfigured_endpoint_stays_200_pending(self, db, client, auth_headers, monkeypatch):
        # hermetic: force "no contract configured" regardless of ambient env
        monkeypatch.setattr(anchor_mod.Config, "EVM_CONTRACT_ADDRESS", "")
        _seed_events(db, count=1, prefix="evm-endpoint-off")

        resp = client.post("/api/forensics/anchor/build", json={"provider": "evm"}, headers=auth_headers)
        assert resp.status_code == 200, resp.get_json()  # contract allows PENDING, never 500
        batch = resp.get_json()["batch"]
        assert batch["provider"] == "evm-sepolia"
        assert batch["status"] == "PENDING"
        assert batch["error"] == EVM_PENDING_ERROR
        assert batch["explorer_url"] is None

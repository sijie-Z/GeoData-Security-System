"""Compile + deploy AnchorRegistry.sol to Sepolia (or an in-memory tester chain).

Usage (from the repo root):

    python contracts/deploy_evm_anchor.py --network tester   # local in-memory chain self-test
    python contracts/deploy_evm_anchor.py                    # Sepolia (default)

Sepolia flow:
  1. generate a key once (prints ONLY the address):
         cd testrealend && python -m evidence.evm --new-key
  2. fund the printed address from a faucet (see contracts/README.md);
  3. run this script — it prints the deployed contract address (and a ready-made
     EVM_CONTRACT_ADDRESS=... line) but NEVER the private key.

The private key is read from testrealend/instance/keys/evm_sepolia.key (git-ignored).
"""

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_FILE = Path(__file__).resolve().parent / "AnchorRegistry.sol"
SOLC_VERSION = "0.8.24"
DEFAULT_RPC = "https://ethereum-sepolia-rpc.publicnode.com"
SEPOLIA_CHAIN_ID = 11155111

sys.path.insert(0, str(REPO_ROOT / "testrealend"))

from evidence.evm import key_file_path, load_private_key  # noqa: E402


def compile_contract():
    """Compile AnchorRegistry.sol with py-solc-x (downloads solc once on first run)."""
    import solcx

    installed = {str(v) for v in solcx.get_installed_solc_versions()}
    if SOLC_VERSION not in installed:
        print(f"installing solc {SOLC_VERSION} (one-time download)...")
        solcx.install_solc(SOLC_VERSION)

    source = CONTRACT_FILE.read_text(encoding="utf-8")
    compiled = solcx.compile_source(source, output_values=["abi", "bin"], solc_version=SOLC_VERSION)
    # compile_source keys are "<stdin>:<ContractName>"; keep the AnchorRegistry entry.
    key = next(k for k in compiled if k.endswith(":AnchorRegistry"))
    data = compiled[key]
    print(f"solc {SOLC_VERSION}: compiled AnchorRegistry, bytecode {len(data['bin']) // 2} bytes")
    return data["abi"], data["bin"]


def deploy_tester(abi, bytecode):
    """Deploy to an in-memory eth-tester chain (no network, no key needed)."""
    from web3 import Web3
    from web3.providers.eth_tester import EthereumTesterProvider

    w3 = Web3(EthereumTesterProvider())
    sender = w3.eth.accounts[0]
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = contract.constructor().transact({"from": sender})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    address = receipt.contractAddress
    print(f"[tester] chain_id={w3.eth.chain_id} deployer={sender}")
    print(f"[tester] AnchorRegistry deployed at {address} (block {receipt.blockNumber})")

    # Round-trip smoke check on the in-memory chain.
    instance = w3.eth.contract(address=address, abi=abi)
    root = bytes.fromhex("11" * 32)
    tx_hash = instance.functions.anchor(root).transact({"from": sender})
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"[tester] anchor() ok, exists={instance.functions.exists(root).call()} "
          f"timestamp={instance.functions.getTimestamp(root).call()}")
    return address


def deploy_sepolia(abi, bytecode, rpc_url):
    """Deploy to Sepolia with the key file; prints addresses only, never the key."""
    from eth_account import Account
    from web3 import Web3
    from web3.middleware import SignAndSendRawMiddlewareBuilder
    from web3.providers.rpc import HTTPProvider

    private_key = load_private_key()
    if not private_key:
        print(f"no private key at {key_file_path()} - run:  cd testrealend && python -m evidence.evm --new-key")
        print("then fund the printed address from a Sepolia faucet (see contracts/README.md)")
        return 2

    account = Account.from_key(private_key)
    w3 = Web3(HTTPProvider(rpc_url, request_kwargs={"timeout": 8}))
    chain_id = w3.eth.chain_id
    if chain_id != SEPOLIA_CHAIN_ID:
        print(f"WARNING: RPC chain_id={chain_id} is not Sepolia ({SEPOLIA_CHAIN_ID}) — check EVM_RPC_URL")

    balance = w3.eth.get_balance(account.address)
    print(f"[sepolia] rpc={rpc_url} chain_id={chain_id}")
    print(f"[sepolia] deployer address: {account.address} (balance {w3.from_wei(balance, 'ether')} ETH)")
    if balance == 0:
        print("deployer balance is 0 — fund it from a faucet first (see contracts/README.md)")
        return 3

    w3.middleware_onion.add(SignAndSendRawMiddlewareBuilder.build(account))
    w3.eth.default_account = account.address
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = contract.constructor().transact({"from": account.address})
    print(f"[sepolia] deploy tx: {tx_hash.hex()} (waiting for receipt...)")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)
    if receipt.status != 1:
        print(f"[sepolia] deployment FAILED (status={receipt.status})")
        return 4
    address = receipt.contractAddress
    print(f"[sepolia] AnchorRegistry deployed at {address} (block {receipt.blockNumber})")
    print(f"[sepolia] explorer: https://sepolia.etherscan.io/address/{address}")
    print(f"[sepolia] add to your env: EVM_CONTRACT_ADDRESS={address}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Compile + deploy the AnchorRegistry contract.")
    parser.add_argument(
        "--network",
        choices=["sepolia", "tester"],
        default="sepolia",
        help="sepolia (default, real testnet) or tester (in-memory chain self-test)",
    )
    parser.add_argument("--rpc", default=os.environ.get("EVM_RPC_URL", DEFAULT_RPC), help="RPC URL (sepolia only)")
    args = parser.parse_args()

    abi, bytecode = compile_contract()
    if args.network == "tester":
        deploy_tester(abi, bytecode)
        return 0
    return deploy_sepolia(abi, bytecode, args.rpc)


if __name__ == "__main__":
    sys.exit(main())

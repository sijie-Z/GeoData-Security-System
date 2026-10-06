"""EVM (Sepolia) anchor support: key-file handling and the wallet CLI.

Discipline: the private key NEVER enters git, logs or API responses. It lives at
``testrealend/instance/keys/evm_sepolia.key`` (the whole ``instance/`` tree is
git-ignored) and is only read by the anchor provider and the deploy script.

CLI (run from ``testrealend/``):

    python -m evidence.evm --new-key    # generate a wallet, prints the ADDRESS only
    python -m evidence.evm --address    # print the stored wallet's address
"""

import argparse
import os
import sys
from pathlib import Path

KEY_ENV_VAR = "EVM_KEY_FILE"
DEFAULT_KEY_PATH = Path(__file__).resolve().parent.parent / "instance" / "keys" / "evm_sepolia.key"


def key_file_path() -> Path:
    """Key file location; overridable via the EVM_KEY_FILE env var (tests/ops)."""
    override = os.environ.get(KEY_ENV_VAR)
    return Path(override) if override else DEFAULT_KEY_PATH


def _normalize_key_hex(text: str) -> str | None:
    text = (text or "").strip()
    if text.startswith("0x"):
        text = text[2:]
    if len(text) == 64 and all(c in "0123456789abcdefABCDEF" for c in text):
        return text.lower()
    return None


def load_private_key(path=None) -> str | None:
    """Return the hex private key, or None when missing/invalid. Never logs it."""
    target = Path(path) if path else key_file_path()
    try:
        raw = target.read_text(encoding="utf-8")
    except OSError:
        return None
    return _normalize_key_hex(raw)


def save_private_key(private_key_hex: str, path=None) -> Path:
    """Persist a key to disk (owner-only perms where the OS supports it)."""
    target = Path(path) if path else key_file_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(private_key_hex, encoding="utf-8")
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass  # Windows ACLs don't map to POSIX bits; best effort only
    return target


def generate_wallet(path=None) -> str:
    """Create a new wallet, store the key at ``path``, return the ADDRESS (never the key)."""
    from eth_account import Account

    account = Account.create()
    key_hex = account.key.hex()
    if key_hex.startswith("0x"):
        key_hex = key_hex[2:]
    save_private_key(key_hex, path)
    return account.address


def address_from_key_file(path=None) -> str | None:
    private_key = load_private_key(path)
    if not private_key:
        return None
    from eth_account import Account

    return Account.from_key(private_key).address


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="EVM anchor wallet helper (prints addresses only - keys are never printed)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--new-key", action="store_true", help="generate a wallet; prints the ADDRESS for faucets")
    group.add_argument("--address", action="store_true", help="print the stored wallet's address")
    parser.add_argument("--force", action="store_true", help="with --new-key: overwrite an existing key file")
    args = parser.parse_args(argv)

    if args.new_key:
        target = key_file_path()
        if target.exists() and not args.force:
            print(f"key file already exists: {target} (refusing to overwrite; use --force to replace)")
            return 1
        address = generate_wallet(target)
        print(f"wallet created: {address}")
        print(f"key stored at: {target} (git-ignored - never commit it)")
        print("fund it from a Sepolia faucet before deploying (see contracts/README.md)")
        return 0

    address = address_from_key_file()
    if not address:
        print(f"no key at {key_file_path()} - run: python -m evidence.evm --new-key")
        return 1
    print(f"address: {address}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

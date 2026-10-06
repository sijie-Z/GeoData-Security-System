"""Tests for the Ed25519 key registry lifecycle (crypto.keys).

F-16: these tests must NEVER write to or delete from the real
``instance/keys/`` directory. Every test monkeypatches ``crypto.keys.KEY_DIR``
to a tmp_path, and an autouse guard asserts the real directory (existence +
mtime/size of the directory and its entries) is exactly the same before and
after each test.
"""

import hashlib
import os

import pytest
from cryptography.hazmat.primitives import serialization

import crypto.keys as keys_mod
from config import BASE_DIR
from crypto.keys import ensure_active_key, get_public_key_by_kid, keyinfo, public_key_fingerprint
from model.key_registry import KeyRegistry

REAL_KEY_DIR = os.path.join(BASE_DIR, "instance", "keys")
ACTIVE_KEY_FILE = "ed25519_active.pem"


def _snapshot(path: str):
    """Existence + mtime/size of the directory and each entry, or None when absent."""
    if not os.path.exists(path):
        return None
    entries = {"<dir>": os.stat(path).st_mtime_ns}
    for name in sorted(os.listdir(path)):
        stat = os.stat(os.path.join(path, name))
        entries[name] = (stat.st_mtime_ns, stat.st_size)
    return entries


@pytest.fixture(autouse=True)
def _real_key_dir_untouched():
    before = _snapshot(REAL_KEY_DIR)
    yield
    assert _snapshot(REAL_KEY_DIR) == before, "test_keys touched the real instance/keys directory"


@pytest.fixture
def key_dir(tmp_path, monkeypatch):
    """Isolated key directory: crypto.keys.KEY_DIR points into tmp_path."""
    target = tmp_path / "keys"
    monkeypatch.setattr(keys_mod, "KEY_DIR", str(target))
    return target


def _raw_public(private_key) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )


class TestEnsureActiveKey:
    def test_first_creation_writes_pem_and_registry_row(self, db, key_dir):
        # Simulate a fresh install: empty (tmp) key dir, no registry rows.
        assert not key_dir.exists()
        KeyRegistry.query.delete()
        db.session.commit()

        kid, private_key = ensure_active_key()

        assert isinstance(kid, int)
        pem_path = key_dir / ACTIVE_KEY_FILE
        assert pem_path.exists()
        assert b"-----BEGIN PRIVATE KEY-----" in pem_path.read_bytes()
        row = KeyRegistry.query.filter_by(kid=kid).first()
        assert row is not None
        assert row.name == "geo-v3-active"
        assert row.status == "active"
        assert bytes(row.public_key) == _raw_public(private_key)

    def test_repeat_ensure_does_not_add_rows(self, db, key_dir):
        ensure_active_key()
        count = KeyRegistry.query.count()
        ensure_active_key()
        ensure_active_key()
        assert KeyRegistry.query.count() == count

    def test_self_heals_registry_row_when_cleared(self, db, key_dir):
        _kid, private_key = ensure_active_key()
        raw_public = _raw_public(private_key)

        KeyRegistry.query.delete()
        db.session.commit()
        assert KeyRegistry.query.count() == 0

        kid_again, _private_key = ensure_active_key()
        assert KeyRegistry.query.count() == 1
        row = KeyRegistry.query.filter_by(kid=kid_again).first()
        assert row is not None
        assert bytes(row.public_key) == raw_public
        assert (
            get_public_key_by_kid(kid_again).public_bytes(
                encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
            )
            == raw_public
        )

    def test_fingerprint_stable_and_matches_sha256(self, db, key_dir):
        kid, private_key = ensure_active_key()
        fingerprint1 = public_key_fingerprint(private_key.public_key())
        fingerprint2 = public_key_fingerprint(private_key.public_key())
        assert fingerprint1 == fingerprint2
        assert len(fingerprint1) == 64
        assert fingerprint1 == hashlib.sha256(_raw_public(private_key)).hexdigest()

        info = keyinfo()
        assert info == {"kid": kid, "algo": "Ed25519", "fingerprint": fingerprint1}

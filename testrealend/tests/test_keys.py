"""Tests for the Ed25519 key registry lifecycle (crypto.keys)."""

import hashlib
import os

from cryptography.hazmat.primitives import serialization

from crypto.keys import KEY_DIR, ensure_active_key, get_public_key_by_kid, keyinfo, public_key_fingerprint
from model.key_registry import KeyRegistry

KEY_PATH = os.path.join(KEY_DIR, "ed25519_active.pem")


def _raw_public(private_key) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )


class TestEnsureActiveKey:
    def test_first_creation_writes_pem_and_registry_row(self, db):
        # Simulate a fresh install: no pem file, no registry rows.
        if os.path.exists(KEY_PATH):
            os.remove(KEY_PATH)
        KeyRegistry.query.delete()
        db.session.commit()

        kid, private_key = ensure_active_key()

        assert isinstance(kid, int)
        assert os.path.exists(KEY_PATH)
        with open(KEY_PATH, "rb") as fh:
            assert b"-----BEGIN PRIVATE KEY-----" in fh.read()
        row = KeyRegistry.query.filter_by(kid=kid).first()
        assert row is not None
        assert row.name == "geo-v3-active"
        assert row.status == "active"
        assert bytes(row.public_key) == _raw_public(private_key)

    def test_repeat_ensure_does_not_add_rows(self, db):
        ensure_active_key()
        count = KeyRegistry.query.count()
        ensure_active_key()
        ensure_active_key()
        assert KeyRegistry.query.count() == count

    def test_self_heals_registry_row_when_cleared(self, db):
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

    def test_fingerprint_stable_and_matches_sha256(self, db):
        kid, private_key = ensure_active_key()
        fingerprint1 = public_key_fingerprint(private_key.public_key())
        fingerprint2 = public_key_fingerprint(private_key.public_key())
        assert fingerprint1 == fingerprint2
        assert len(fingerprint1) == 64
        assert fingerprint1 == hashlib.sha256(_raw_public(private_key)).hexdigest()

        info = keyinfo()
        assert info == {"kid": kid, "algo": "Ed25519", "fingerprint": fingerprint1}

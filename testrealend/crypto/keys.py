"""Ed25519 key management for v3 delivery signing.

Private keys live ONLY under ``instance/keys/`` (gitignored) — the database
(KeyRegistry) stores public material only. ``ensure_active_key`` is idempotent
and self-healing so rebuilt/empty databases never block signing.
"""

import hashlib
import os
from datetime import UTC, datetime

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from config import BASE_DIR
from extension.extension import db
from model.key_registry import KeyRegistry

KEY_DIR = os.path.join(BASE_DIR, "instance", "keys")
ACTIVE_KEY_FILE = "ed25519_active.pem"
ACTIVE_KEY_NAME = "geo-v3-active"


def _key_path() -> str:
    return os.path.join(KEY_DIR, ACTIVE_KEY_FILE)


def _save_private_key(path: str, private_key: ed25519.Ed25519PrivateKey) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with open(path, "wb") as fh:
        fh.write(pem)
    try:
        os.chmod(path, 0o600)  # best effort — a no-op on some Windows setups
    except OSError:
        pass


def _load_private_key(path: str) -> ed25519.Ed25519PrivateKey:
    with open(path, "rb") as fh:
        private_key = serialization.load_pem_private_key(fh.read(), password=None)
    if not isinstance(private_key, ed25519.Ed25519PrivateKey):
        raise ValueError(f"{path} does not contain an Ed25519 private key")
    return private_key


def _raw_public_bytes(private_key: ed25519.Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )


def ensure_active_key():
    """Return ``(kid, private_key)`` for the active signing key.

    Loads (or generates and persists) ``instance/keys/ed25519_active.pem`` and
    guarantees a matching KeyRegistry row exists — the row is re-inserted if it
    went missing (e.g. a rebuilt test database). Assumes a single writer.
    """
    path = _key_path()
    if os.path.exists(path):
        private_key = _load_private_key(path)
    else:
        private_key = ed25519.Ed25519PrivateKey.generate()
        _save_private_key(path, private_key)

    public_raw = _raw_public_bytes(private_key)
    row = KeyRegistry.query.filter_by(public_key=public_raw).first()
    if row is None:
        row = KeyRegistry(
            name=ACTIVE_KEY_NAME,
            public_key=public_raw,
            status="active",
            created_at=datetime.now(UTC),
        )
        db.session.add(row)
        db.session.commit()
    return row.kid, private_key


def get_public_key_by_kid(kid: int) -> ed25519.Ed25519PublicKey:
    """Look up an Ed25519 public key by kid. Raises KeyError when unknown.

    The registry ``status`` column is deliberately NOT checked: historical
    signatures must remain verifiable forever, so retired or revoked keys stay
    resolvable for verification (status gates signing, not verification).
    """
    row = KeyRegistry.query.filter_by(kid=kid).first()
    if row is None:
        raise KeyError(f"unknown kid: {kid}")
    return ed25519.Ed25519PublicKey.from_public_bytes(bytes(row.public_key))


def get_public_keys_by_kids(kids) -> dict[int, ed25519.Ed25519PublicKey]:
    """Batch variant of :func:`get_public_key_by_kid` — one ``IN`` query.

    Unknown kids are simply absent from the returned map, so callers that need
    ``get_public_key_by_kid``'s KeyError contract (e.g. ``evidence.chain``)
    can distinguish "kid not registered" by a missing dict key.
    """
    unique_kids = {int(kid) for kid in kids if kid is not None}
    if not unique_kids:
        return {}
    rows = KeyRegistry.query.filter(KeyRegistry.kid.in_(unique_kids)).all()
    return {row.kid: ed25519.Ed25519PublicKey.from_public_bytes(bytes(row.public_key)) for row in rows}


def public_key_fingerprint(pub) -> str:
    """sha256 over the 32-byte raw public key, as the full 64-char hex digest."""
    raw = pub.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()


def keyinfo() -> dict:
    """Active-key summary: ``{"kid": .., "algo": "Ed25519", "fingerprint": ..}``."""
    kid, private_key = ensure_active_key()
    return {"kid": kid, "algo": "Ed25519", "fingerprint": public_key_fingerprint(private_key.public_key())}

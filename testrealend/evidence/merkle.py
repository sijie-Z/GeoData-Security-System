"""Merkle tree over event hashes (RFC 6962-style domain separation, position-bound).

  leaf   = sha256(DOMAIN_LEAF || uint32be(n) || uint32be(i) || raw_event_hash)
  parent = sha256(DOMAIN_MERKLE || left || right)

``n`` is the total number of leaves and ``i`` the 0-based leaf position, so the
leaf domain commits to both the batch size and the position: a 3-leaf tree can
no longer collide with a 4-leaf tree whose last leaf was duplicated. Odd
levels duplicate the last node before pairing (merge rule unchanged).
Empty input -> None; a single leaf returns its leaf hash hex.
"""

import hashlib
import struct

from evidence.constants import DOMAIN_LEAF, DOMAIN_MERKLE


def _hash(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _leaf_hash(event_hash: str, total: int, index: int) -> bytes:
    """Position-bound leaf hash. Non-hex / non-32-byte input raises ValueError."""
    try:
        raw = bytes.fromhex(event_hash)
    except (TypeError, ValueError) as e:
        raise ValueError("invalid event hash") from e
    if len(raw) != 32:
        raise ValueError("invalid event hash")
    return _hash(DOMAIN_LEAF + struct.pack(">II", total, index) + raw)


def merkle_root(event_hashes: list[str]):
    """Merkle root (hex str) for the given event hashes, or None for an empty list."""
    if not event_hashes:
        return None
    total = len(event_hashes)
    level = [_leaf_hash(event_hash, total, index) for index, event_hash in enumerate(event_hashes)]
    while len(level) > 1:
        if len(level) % 2 == 1:
            level = [*level, level[-1]]
        level = [_hash(DOMAIN_MERKLE + level[i] + level[i + 1]) for i in range(0, len(level), 2)]
    return level[0].hex()

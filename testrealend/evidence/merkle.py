"""Merkle tree over event hashes (RFC 6962-style domain separation).

  leaf   = sha256(DOMAIN_LEAF   || raw_event_hash)
  parent = sha256(DOMAIN_MERKLE || left || right)

Odd levels duplicate the last node before pairing. Empty input -> None;
a single leaf returns its leaf hash hex.
"""

import hashlib

from evidence.constants import DOMAIN_LEAF, DOMAIN_MERKLE


def _hash(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def merkle_root(event_hashes: list[str]):
    """Merkle root (hex str) for the given event hashes, or None for an empty list."""
    if not event_hashes:
        return None
    level = [_hash(DOMAIN_LEAF + bytes.fromhex(event_hash)) for event_hash in event_hashes]
    while len(level) > 1:
        if len(level) % 2 == 1:
            level = [*level, level[-1]]
        level = [_hash(DOMAIN_MERKLE + level[i] + level[i + 1]) for i in range(0, len(level), 2)]
    return level[0].hex()

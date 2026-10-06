"""COSE_Sign1 (RFC 9052) signing/verification with Ed25519 (RFC 9053).

Wire format: CBOR array [protected: bstr, unprotected: map, payload: bstr,
signature: bstr], serialised WITHOUT a CBOR tag 18. The parser additionally
accepts tag-18-wrapped input for interoperability.

Decoding is strict: the input must be exactly one CBOR item (trailing bytes
are rejected, A-1) and the unprotected header must be empty (B-1) — this
system only ever signs with everything in the protected header.

The signing input is the canonical-CBOR ``Sig_structure``:
["Signature1", protected_bstr, external_aad="", payload_bstr].

Note: cbor2 >= 6 may hand back immutable containers (tuple/frozendict) when a
tag is involved, so everything is normalised to plain list/dict right after
decoding — structural checks must not depend on cbor2's decode flavours.
"""

import io
from collections.abc import Mapping

import cbor2

from crypto import canonical

ALG_EDDSA = -8
COSE_SIGN1_TAG = 18


class QrPayloadError(Exception):
    """Umbrella error for unparseable or untrusted QR v2 payload text.

    ``crypto.payload.parse_qr_text`` converts every failure mode (invalid
    base64url framing, CBOR/COSE structural errors, unknown kid, missing
    fields, payload/protected kid mismatch) into this type. ``CoseVerifyError``
    is the more specific subclass raised by the COSE layer itself.
    """


class CoseVerifyError(QrPayloadError):
    """Raised when a COSE_Sign1 message fails structural or signature validation."""


def _to_plain(obj):
    """Recursively convert tuple -> list and any Mapping -> dict."""
    if isinstance(obj, (tuple, list)):
        return [_to_plain(item) for item in obj]
    if isinstance(obj, Mapping):
        return {key: _to_plain(value) for key, value in obj.items()}
    return obj


def _decode_structure(cose_bytes: bytes):
    """Parse a COSE_Sign1 message into (protected_bstr, protected_map, unprotected, payload, signature).

    Rejects trailing bytes after the CBOR message (A-1): appended garbage must
    never be silently ignored when verifying a signed payload.
    """
    stream = io.BytesIO(cose_bytes)
    try:
        obj = cbor2.CBORDecoder(stream).decode()
    except Exception as e:
        raise CoseVerifyError(f"CBOR decode failed: {e}") from e
    if stream.read(1):
        raise CoseVerifyError("trailing bytes after COSE_Sign1 message")
    if isinstance(obj, cbor2.CBORTag):
        if obj.tag != COSE_SIGN1_TAG:
            raise CoseVerifyError(f"unexpected CBOR tag {obj.tag}, expected {COSE_SIGN1_TAG} (COSE_Sign1)")
        obj = obj.value
    obj = _to_plain(obj)
    if not isinstance(obj, list) or len(obj) != 4:
        raise CoseVerifyError("COSE_Sign1 must be a 4-element array [protected, unprotected, payload, signature]")
    protected_bstr, unprotected, payload, signature = obj
    if not isinstance(protected_bstr, bytes):
        raise CoseVerifyError("protected header must be a bstr")
    if not isinstance(unprotected, dict):
        raise CoseVerifyError("unprotected header must be a map")
    if not isinstance(payload, bytes):
        raise CoseVerifyError("payload must be a bstr")
    if not isinstance(signature, bytes):
        raise CoseVerifyError("signature must be a bstr")
    try:
        protected = _to_plain(cbor2.loads(protected_bstr))
    except Exception as e:
        raise CoseVerifyError(f"protected header decode failed: {e}") from e
    if not isinstance(protected, dict):
        raise CoseVerifyError("protected header must decode to a map")
    return protected_bstr, protected, unprotected, payload, signature


def _sig_structure(protected_bstr: bytes, payload: bytes) -> bytes:
    """Sig_structure (RFC 9052 §4.4) with empty external_aad."""
    return canonical.dumps(["Signature1", protected_bstr, b"", payload])


def sign1_sign(payload: bytes, kid: int, private_key) -> bytes:
    """Create a COSE_Sign1 message. ``private_key`` is an Ed25519PrivateKey from cryptography."""
    protected_bstr = canonical.dumps({"alg": ALG_EDDSA, "kid": kid})
    signature = private_key.sign(_sig_structure(protected_bstr, payload))
    return cbor2.dumps([protected_bstr, {}, payload, signature], canonical=True)


def decode_sign1_protected(cose_bytes: bytes) -> dict:
    """Return only the protected header (used to discover the signing kid before key lookup)."""
    protected_bstr, protected, _unprotected, _payload, _signature = _decode_structure(cose_bytes)
    return protected


def sign1_verify(cose_bytes: bytes, public_key) -> bytes:
    """Verify a COSE_Sign1 message and return its payload, or raise CoseVerifyError."""
    protected_bstr, protected, unprotected, payload, signature = _decode_structure(cose_bytes)
    # B-1: this system always signs with everything in the protected header, so
    # a non-empty unprotected header is either tampering or a protocol error.
    if unprotected:
        raise CoseVerifyError("unprotected header must be empty")
    # A-2: alg must be the exact integer -8; float -8.0 (or bools) are rejected.
    alg = protected.get("alg")
    if not (isinstance(alg, int) and not isinstance(alg, bool) and alg == ALG_EDDSA):
        raise CoseVerifyError(f"unsupported alg {alg!r}, expected {ALG_EDDSA} (EdDSA)")
    try:
        public_key.verify(signature, _sig_structure(protected_bstr, payload))
    except Exception as e:
        raise CoseVerifyError(f"signature verification failed: {e}") from e
    return payload

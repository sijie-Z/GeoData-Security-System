"""QR text payload v2: COSE_Sign1 over canonical CBOR, base64url "GDS2:" framing.

v1 texts (anything without the "GDS2:" prefix) are passed through untouched so
the legacy handling path can decide what to do with them.
"""

import base64

from crypto import canonical
from crypto.cose import QrPayloadError, decode_sign1_protected, sign1_sign, sign1_verify
from crypto.keys import ensure_active_key, get_public_key_by_kid

V2_PREFIX = "GDS2:"


def is_v2_text(text) -> bool:
    """True when ``text`` carries the v2 signed-payload prefix."""
    return isinstance(text, str) and text.startswith(V2_PREFIX)


def build_qr_v2_text(fid_hex: str, delivery_id: int, kid: int, issued_at_epoch: int) -> str:
    """Build the signed v2 QR text for one delivery.

    ``fid_hex`` is the hex artifact fingerprint. ``kid`` must be the id of the
    active signing key (the one whose private half signs here), i.e. normally
    the kid returned by ``ensure_active_key()``.
    """
    _active_kid, private_key = ensure_active_key()
    payload_cbor = canonical.dumps(
        {
            "v": 2,
            "kid": kid,
            "fid": bytes.fromhex(fid_hex),
            "delivery": delivery_id,
            "issued_at": issued_at_epoch,
        }
    )
    cose = sign1_sign(payload_cbor, kid, private_key)
    return V2_PREFIX + base64.urlsafe_b64encode(cose).rstrip(b"=").decode()


def parse_qr_text(text: str) -> dict:
    """Parse QR text into structured fields.

    v2 ("GDS2:" prefix): base64url-decode, verify the COSE_Sign1 signature with
    the public key looked up from KeyRegistry by the header kid, and return
    ``{"version": 2, "kid", "fid_hex", "delivery", "issued_at"}``.

    Anything else is v1 legacy text: ``{"version": 1, "raw": text}``.

    Failure contract (B-2): every malformed or untrusted v2 input raises
    ``QrPayloadError`` — invalid base64url framing (strict decode, trailing
    bytes rejected), non-CBOR bytes, COSE structural/signature failures
    (``CoseVerifyError``, a ``QrPayloadError`` subclass), unknown kid, missing
    or mistyped fields, payload/protected kid mismatch (B-3), and unsupported
    payload versions. No other exception type escapes.
    """
    if not is_v2_text(text):
        return {"version": 1, "raw": text}

    body = text[len(V2_PREFIX) :]
    try:
        padded = body + "=" * (-len(body) % 4)
        cose = base64.b64decode(padded, altchars=b"-_", validate=True)
    except ValueError as e:  # binascii.Error is a ValueError subclass
        raise QrPayloadError(f"invalid base64url body: {e}") from e

    protected = decode_sign1_protected(cose)
    header_kid = protected.get("kid")
    try:
        public_key = get_public_key_by_kid(header_kid)
    except KeyError as e:
        raise QrPayloadError(f"unknown kid: {header_kid!r}") from e
    payload_cbor = sign1_verify(cose, public_key)
    try:
        payload = canonical.loads(payload_cbor)
    except Exception as e:
        raise QrPayloadError(f"payload is not canonical CBOR: {e}") from e
    if not isinstance(payload, dict):
        raise QrPayloadError("payload must decode to a map")
    if payload.get("v") != 2:
        raise QrPayloadError(f"unsupported GDS2 payload version: {payload.get('v')!r}")
    # B-3: the signed payload's kid must agree with the signature header kid.
    if payload.get("kid") != header_kid:
        raise QrPayloadError(f"payload kid {payload.get('kid')!r} does not match protected header kid {header_kid!r}")
    fid = payload.get("fid")
    if not isinstance(fid, bytes):
        raise QrPayloadError("payload fid field must be bytes")
    try:
        return {
            "version": 2,
            "kid": payload["kid"],
            "fid_hex": fid.hex(),
            "delivery": payload["delivery"],
            "issued_at": payload["issued_at"],
        }
    except KeyError as e:
        raise QrPayloadError(f"missing payload field: {e}") from e

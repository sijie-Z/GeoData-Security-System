"""QR text payload v2: COSE_Sign1 over canonical CBOR, base64url "GDS2:" framing.

v1 texts (anything without the "GDS2:" prefix) are passed through untouched so
the legacy handling path can decide what to do with them.
"""

import base64

from crypto import canonical
from crypto.cose import decode_sign1_protected, sign1_sign, sign1_verify
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
    """
    if not is_v2_text(text):
        return {"version": 1, "raw": text}

    body = text[len(V2_PREFIX) :]
    padded = body + "=" * (-len(body) % 4)
    cose = base64.urlsafe_b64decode(padded)
    protected = decode_sign1_protected(cose)
    public_key = get_public_key_by_kid(protected.get("kid"))
    payload_cbor = sign1_verify(cose, public_key)
    payload = canonical.loads(payload_cbor)
    if payload.get("v") != 2:
        raise ValueError(f"unsupported GDS2 payload version: {payload.get('v')!r}")
    return {
        "version": 2,
        "kid": payload["kid"],
        "fid_hex": bytes(payload["fid"]).hex(),
        "delivery": payload["delivery"],
        "issued_at": payload["issued_at"],
    }

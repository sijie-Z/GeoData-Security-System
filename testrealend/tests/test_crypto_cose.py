"""Tests for canonical CBOR encoding, COSE_Sign1 round-trips and the QR v2 payload."""

import base64

import cbor2
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from crypto import canonical
from crypto.cose import CoseVerifyError, QrPayloadError, sign1_sign, sign1_verify
from crypto.keys import ensure_active_key
from crypto.payload import build_qr_v2_text, is_v2_text, parse_qr_text


class TestCanonical:
    def test_deterministic_regardless_of_insertion_order(self):
        a = canonical.dumps({"b": 2, "a": 1, "c": {"y": b"z", "x": [1, None, True]}})
        b = canonical.dumps({"a": 1, "c": {"x": [1, None, True], "y": b"z"}, "b": 2})
        assert a == b

    def test_float_rejected(self):
        with pytest.raises(ValueError):
            canonical.dumps(1.5)
        with pytest.raises(ValueError):
            canonical.dumps({"nested": [0.25]})

    def test_non_finite_floats_rejected(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with pytest.raises(ValueError):
                canonical.dumps({"x": bad})

    def test_deeply_nested_float_key_rejected(self):
        with pytest.raises(ValueError):
            canonical.dumps({"outer": [{"inner": {3.5: "v"}}]})

    def test_tuple_and_bytearray_rejected(self):
        with pytest.raises(ValueError):
            canonical.dumps({"t": (1, 2)})
        with pytest.raises(ValueError):
            canonical.dumps({"b": bytearray(b"ab")})

    def test_large_integer_encoding_stable(self):
        value = 2**70
        encoded = canonical.dumps({"n": value})
        assert encoded == b"\xa1an\xc2I" + b"\x40" + b"\x00" * 8  # bignum tag 2, 9 bytes
        assert canonical.dumps({"n": value}) == encoded
        assert canonical.loads(encoded) == {"n": value}

    def test_mixed_length_key_ordering_canonical(self):
        a = canonical.dumps({"aa": 1, "b": 2, "zzz": 4, "": 3})
        b = canonical.dumps({"zzz": 4, "": 3, "b": 2, "aa": 1})
        assert a == b  # length-first then bytewise ordering is deterministic

    def test_lone_surrogate_surfaces_as_value_error(self):
        """A-3: encoding failures inside cbor2 are wrapped as ValueError."""
        with pytest.raises(ValueError):
            canonical.dumps({"bad": "\ud800"})

    def test_bytes_and_nested_roundtrip(self):
        obj = {"bin": b"\x00\xff\x10", "nested": [1, True, None, "s", {"k": b"v"}, [b""]], "n": -42}
        assert canonical.loads(canonical.dumps(obj)) == obj

    def test_non_str_dict_key_rejected(self):
        with pytest.raises(ValueError):
            canonical.dumps({1: "x"})

    def test_unsupported_type_rejected(self):
        with pytest.raises(ValueError):
            canonical.dumps({"bad": object()})


class TestCoseSign1:
    @pytest.fixture
    def keypair(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        return private_key, private_key.public_key()

    def test_roundtrip(self, keypair):
        private_key, public_key = keypair
        payload = canonical.dumps({"v": 2, "note": "hello"})
        cose = sign1_sign(payload, 7, private_key)
        assert sign1_verify(cose, public_key) == payload

    def test_tampered_payload_bit_flip_rejected(self, keypair):
        private_key, public_key = keypair
        payload = canonical.dumps({"v": 2, "n": 1})
        cose = sign1_sign(payload, 1, private_key)
        obj = cbor2.loads(cose)
        obj[2] = bytes([payload[0] ^ 0x01]) + payload[1:]
        with pytest.raises(CoseVerifyError):
            sign1_verify(cbor2.dumps(obj, canonical=True), public_key)

    def test_tampered_signature_rejected(self, keypair):
        private_key, public_key = keypair
        cose = sign1_sign(b"data", 1, private_key)
        obj = cbor2.loads(cose)
        signature = bytearray(obj[3])
        signature[0] ^= 0x01
        obj[3] = bytes(signature)
        with pytest.raises(CoseVerifyError):
            sign1_verify(cbor2.dumps(obj, canonical=True), public_key)

    def test_tag18_wrapped_input_accepted(self, keypair):
        private_key, public_key = keypair
        payload = b"tagged payload"
        cose = sign1_sign(payload, 1, private_key)
        tagged = cbor2.dumps(cbor2.CBORTag(18, cbor2.loads(cose)))
        assert sign1_verify(tagged, public_key) == payload

    def test_wrong_tag_rejected(self, keypair):
        private_key, public_key = keypair
        cose = sign1_sign(b"x", 1, private_key)
        with pytest.raises(CoseVerifyError):
            sign1_verify(cbor2.dumps(cbor2.CBORTag(99, cbor2.loads(cose))), public_key)

    def test_wrong_public_key_rejected(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        other_public_key = ed25519.Ed25519PrivateKey.generate().public_key()
        cose = sign1_sign(b"x", 1, private_key)
        with pytest.raises(CoseVerifyError):
            sign1_verify(cose, other_public_key)

    def test_verify_error_is_qr_payload_error_subclass(self):
        assert issubclass(CoseVerifyError, QrPayloadError)

    def test_nonempty_unprotected_header_rejected(self):
        """B-1: the unprotected header is not covered by the signature; this
        system always signs with {} and must reject a non-empty one."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        cose = sign1_sign(b"data", 1, private_key)
        obj = cbor2.loads(cose)
        obj[1] = {"kid": 999, "crit": True}
        with pytest.raises(CoseVerifyError):
            sign1_verify(cbor2.dumps(obj, canonical=True), public_key)

    def test_trailing_bytes_after_message_rejected(self):
        """A-1: appended garbage after a valid COSE message must be rejected."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        cose = sign1_sign(b"payload", 1, private_key)
        with pytest.raises(CoseVerifyError):
            sign1_verify(cose + b"\xff", public_key)
        tagged = cbor2.dumps(cbor2.CBORTag(18, cbor2.loads(cose)))
        with pytest.raises(CoseVerifyError):
            sign1_verify(tagged + b"\x00", public_key)

    def test_alg_float_rejected(self):
        """A-2: -8.0 == -8 in Python; the alg check must be type-strict."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        payload = b"data"
        protected_bstr = cbor2.dumps({"alg": -8.0, "kid": 1})
        signature = private_key.sign(canonical.dumps(["Signature1", protected_bstr, b"", payload]))
        cose = cbor2.dumps([protected_bstr, {}, payload, signature], canonical=True)
        with pytest.raises(CoseVerifyError):
            sign1_verify(cose, public_key)

    def test_alg_int_other_than_eddsa_rejected(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        payload = b"data"
        protected_bstr = canonical.dumps({"alg": -7, "kid": 1})
        signature = private_key.sign(canonical.dumps(["Signature1", protected_bstr, b"", payload]))
        cose = cbor2.dumps([protected_bstr, {}, payload, signature], canonical=True)
        with pytest.raises(CoseVerifyError):
            sign1_verify(cose, public_key)


class TestQrV2Payload:
    @staticmethod
    def _to_text(cose_bytes: bytes) -> str:
        return "GDS2:" + base64.urlsafe_b64encode(cose_bytes).rstrip(b"=").decode()

    def test_build_then_parse_roundtrip(self, db):
        kid, _private_key = ensure_active_key()
        fid_hex = "0123456789abcdef" * 2
        text = build_qr_v2_text(fid_hex, delivery_id=123, kid=kid, issued_at_epoch=1730000000)
        assert text.startswith("GDS2:")
        assert is_v2_text(text)
        parsed = parse_qr_text(text)
        assert parsed == {"version": 2, "kid": kid, "fid_hex": fid_hex, "delivery": 123, "issued_at": 1730000000}

    def test_v1_text_passthrough(self):
        assert parse_qr_text("LEGACY-TEXT-123") == {"version": 1, "raw": "LEGACY-TEXT-123"}
        assert not is_v2_text("LEGACY-TEXT-123")

    def test_tampered_v2_text_rejected(self, db):
        kid, _private_key = ensure_active_key()
        text = build_qr_v2_text("ab" * 16, 1, kid, 1730000000)
        body = text[len("GDS2:") :]
        cose = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        obj = cbor2.loads(cose)
        obj[2] = b"garbage payload"
        forged_body = base64.urlsafe_b64encode(cbor2.dumps(obj, canonical=True)).rstrip(b"=").decode()
        with pytest.raises(CoseVerifyError):
            parse_qr_text("GDS2:" + forged_body)

    def test_malformed_base64url_framing_rejected(self):
        """B-2: length ≡ 1 mod 4 and out-of-alphabet chars both raise QrPayloadError."""
        for text in ("GDS2:AAAAA", "GDS2:AAEC!!"):
            with pytest.raises(QrPayloadError):
                parse_qr_text(text)

    def test_non_cbor_body_rejected(self):
        """B-2: "____" decodes to b"\\xff\\xff\\xff" — a break marker outside any CBOR item."""
        with pytest.raises(QrPayloadError):
            parse_qr_text("GDS2:____")

    def test_unknown_kid_rejected(self, db):
        """B-2: a validly signed payload whose header kid is not registered."""
        rogue = ed25519.Ed25519PrivateKey.generate()
        payload_cbor = canonical.dumps({"v": 2, "kid": 999999, "fid": b"\x01" * 16, "delivery": 1, "issued_at": 1})
        text = self._to_text(sign1_sign(payload_cbor, 999999, rogue))
        with pytest.raises(QrPayloadError):
            parse_qr_text(text)

    def test_payload_protected_kid_mismatch_rejected(self, db):
        """B-3: payload kid must equal the protected header kid."""
        kid, private_key = ensure_active_key()
        payload_cbor = canonical.dumps({"v": 2, "kid": kid + 777, "fid": b"\x02" * 16, "delivery": 5, "issued_at": 1})
        text = self._to_text(sign1_sign(payload_cbor, kid, private_key))
        with pytest.raises(QrPayloadError):
            parse_qr_text(text)

    def test_trailing_bytes_after_valid_message_rejected(self, db):
        """A-1 through the QR pipeline: garbage appended to a genuine message."""
        kid, _private_key = ensure_active_key()
        text = build_qr_v2_text("ab" * 16, 1, kid, 1730000000)
        body = text[len("GDS2:") :]
        cose = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        with pytest.raises(QrPayloadError):
            parse_qr_text(self._to_text(cose + b"\xff"))

    def test_missing_payload_field_rejected(self, db):
        """B-2: a signed payload missing a required field is a QrPayloadError."""
        kid, private_key = ensure_active_key()
        payload_cbor = canonical.dumps({"v": 2, "kid": kid, "fid": b"\x03" * 16, "issued_at": 1})  # no delivery
        text = self._to_text(sign1_sign(payload_cbor, kid, private_key))
        with pytest.raises(QrPayloadError):
            parse_qr_text(text)

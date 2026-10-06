"""Tests for canonical CBOR encoding, COSE_Sign1 round-trips and the QR v2 payload."""

import base64

import cbor2
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from crypto import canonical
from crypto.cose import CoseVerifyError, sign1_sign, sign1_verify
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


class TestQrV2Payload:
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

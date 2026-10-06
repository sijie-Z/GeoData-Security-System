"""Canonical CBOR encoding with a strict type whitelist (ADR §4.2).

Only int / bool / None / bytes / str / list / dict-with-str-keys are allowed so
that payloads are byte-for-byte identical wherever they are re-serialised
(signature replay guarantee). Floats are rejected outright: they have multiple
valid CBOR encodings and would make the encoding ambiguous.
"""

import cbor2


def _validate(obj):
    if obj is None or isinstance(obj, bool):
        return
    if isinstance(obj, int):
        return
    if isinstance(obj, (bytes, str)):
        return
    if isinstance(obj, float):
        raise ValueError("float is not allowed in canonical CBOR payloads (ADR §4.2)")
    if isinstance(obj, list):
        for item in obj:
            _validate(item)
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            if not isinstance(key, str):
                raise ValueError(f"canonical CBOR dict keys must be str, got {type(key).__name__}")
            _validate(value)
        return
    raise ValueError(f"unsupported type in canonical CBOR payload: {type(obj).__name__}")


def dumps(obj) -> bytes:
    """Recursively whitelist-check ``obj``, then encode with cbor2 canonical mode."""
    _validate(obj)
    return cbor2.dumps(obj, canonical=True)


def loads(data: bytes):
    """Decode canonical CBOR bytes back to Python objects."""
    return cbor2.loads(data)

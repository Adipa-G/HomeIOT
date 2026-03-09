import binascii


SCHEME = "uid-sha256-xor-v1"
SALT = b"homeiot-config-secrets-v1"


def encrypt_secret(plaintext: str, binding_value: str, field_name: str) -> dict:
    nonce = _random_bytes(16)
    key = _derive_key(binding_value, field_name)
    plaintext_bytes = plaintext.encode("utf-8")
    stream = _keystream(key, nonce, len(plaintext_bytes))
    ciphertext = _xor_bytes(plaintext_bytes, stream)
    tag = _sha256(key + nonce + ciphertext)

    return {
        "scheme": SCHEME,
        "nonce": _to_hex(nonce),
        "ciphertext": _to_hex(ciphertext),
        "tag": _to_hex(tag),
    }


def decrypt_secret(payload: dict, binding_value: str, field_name: str) -> str:
    scheme = payload.get("scheme")
    if scheme != SCHEME:
        raise ValueError("Unsupported secret scheme: " + str(scheme))

    nonce = _from_hex(payload["nonce"])
    ciphertext = _from_hex(payload["ciphertext"])
    expected_tag = _from_hex(payload["tag"])

    key = _derive_key(binding_value, field_name)
    actual_tag = _sha256(key + nonce + ciphertext)
    if actual_tag != expected_tag:
        raise ValueError("Secret integrity check failed")

    stream = _keystream(key, nonce, len(ciphertext))
    plaintext = _xor_bytes(ciphertext, stream)
    return plaintext.decode("utf-8")


def _derive_key(binding_value: str, field_name: str) -> bytes:
    material = SALT + b"|" + binding_value.encode("utf-8") + b"|" + field_name.encode("utf-8")
    return _sha256(material)


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < length:
        out += _sha256(key + nonce + _u32be(counter))
        counter += 1
    return out[:length]


def _u32be(value: int) -> bytes:
    return bytes(
        [
            (value >> 24) & 0xFF,
            (value >> 16) & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF,
        ]
    )


def _sha256(data: bytes) -> bytes:
    try:
        import uhashlib as hashlib
    except ImportError:  # pragma: no cover - desktop fallback
        import hashlib
    return hashlib.sha256(data).digest()


def _random_bytes(length: int) -> bytes:
    try:
        import os

        return os.urandom(length)
    except Exception as exc:
        raise RuntimeError("No secure random source available") from exc


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes([a ^ b for a, b in zip(left, right)])


def _to_hex(data: bytes) -> str:
    return binascii.hexlify(data).decode("ascii")


def _from_hex(data: str) -> bytes:
    return binascii.unhexlify(data.encode("ascii"))
from __future__ import annotations

import hashlib
import hmac
import os

from cryptography.fernet import Fernet

from backend.app.core.config import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key_material = settings.get_secret_key().encode()
        derived = hashlib.sha256(key_material).digest()
        import base64
        fernet_key = base64.urlsafe_b64encode(derived)
        _fernet = Fernet(fernet_key)
    return _fernet


def encrypt_value(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def mask_secret(value: str, visible_chars: int = 4) -> str:
    if len(value) <= visible_chars:
        return "****"
    return value[:visible_chars] + "****" + value[-2:]


def generate_correlation_id() -> str:
    return os.urandom(8).hex()


def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())

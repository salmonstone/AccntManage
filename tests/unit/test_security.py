from __future__ import annotations

import pytest

from backend.app.core.security import (
    constant_time_compare,
    decrypt_value,
    encrypt_value,
    generate_correlation_id,
    mask_secret,
)


def test_encrypt_decrypt():
    original = "my-secret-token"
    encrypted = encrypt_value(original)
    assert encrypted != original
    assert decrypt_value(encrypted) == original


def test_mask_secret():
    assert mask_secret("abcdefgh", 4) == "abcd****gh"
    assert mask_secret("ab", 4) == "****"


def test_correlation_id():
    cid = generate_correlation_id()
    assert len(cid) == 16
    assert cid.isalnum()


def test_constant_time_compare():
    assert constant_time_compare("abc", "abc") is True
    assert constant_time_compare("abc", "def") is False

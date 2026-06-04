"""Password hashing + JWT issuance/verification."""

from __future__ import annotations

import jwt
import pytest

from src.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("s3cret-pass")
    assert h != "s3cret-pass"
    assert verify_password("s3cret-pass", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip_carries_user_id():
    token = create_access_token(123)
    payload = decode_access_token(token)
    assert payload["sub"] == "123"


def test_jwt_rejects_tampered_token():
    token = create_access_token(1)
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token + "tampered")

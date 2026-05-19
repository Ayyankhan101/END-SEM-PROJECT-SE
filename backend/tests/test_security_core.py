"""
WB-01, WB-02: White box tests for core security functions.
Tests internal logic: token creation, expiry, blacklist, TOTP, encryption.
"""
import os
import pytest
from datetime import timedelta, datetime
from unittest.mock import patch, MagicMock

# Env set in conftest before app imports
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
    revoke_token,
    encrypt_secret,
    decrypt_secret,
    _token_blacklist_cache,
)
from fastapi import HTTPException


# ─── WB-01: Password hashing ──────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_produces_different_output_than_input(self):
        h = get_password_hash("MyPassword123!")
        assert h != "MyPassword123!"

    def test_verify_correct_password(self):
        h = get_password_hash("CorrectHorse99!")
        assert verify_password("CorrectHorse99!", h) is True

    def test_verify_wrong_password(self):
        h = get_password_hash("CorrectHorse99!")
        assert verify_password("WrongHorse99!", h) is False

    def test_same_password_different_hashes(self):
        """bcrypt salts must differ each call."""
        h1 = get_password_hash("SamePass123!")
        h2 = get_password_hash("SamePass123!")
        assert h1 != h2

    def test_empty_string_hashes(self):
        h = get_password_hash("")
        assert verify_password("", h) is True

    def test_wrong_password_returns_false_not_exception(self):
        h = get_password_hash("ValidPass123!")
        result = verify_password("wrong", h)
        assert result is False


# ─── WB-01: JWT token creation & verification ─────────────────────────────────

class TestJWTTokens:
    def test_access_token_created_successfully(self):
        token = create_access_token({"sub": "testuser", "role": "admin"})
        assert isinstance(token, str)
        assert len(token) > 10

    def test_access_token_payload_round_trips(self):
        token = create_access_token({"sub": "testuser", "role": "viewer"})
        payload = verify_token(token)
        assert payload["sub"] == "testuser"
        assert payload["role"] == "viewer"
        assert payload["type"] == "access"

    def test_refresh_token_has_correct_type(self):
        token = create_refresh_token({"sub": "testuser"})
        payload = verify_token(token)
        assert payload["type"] == "refresh"

    def test_expired_token_raises_401(self):
        token = create_access_token(
            {"sub": "testuser"},
            expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_invalid_token_string_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_token("this.is.not.a.valid.jwt")
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self):
        token = create_access_token({"sub": "testuser"})
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException) as exc_info:
            verify_token(tampered)
        assert exc_info.value.status_code == 401

    def test_revoked_token_raises_401(self):
        token = create_access_token({"sub": "revokeuser"})
        revoke_token(token)
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401
        assert "revoked" in exc_info.value.detail.lower()

    def test_fresh_flag_set_correctly(self):
        token = create_access_token({"sub": "testuser"}, fresh=True)
        payload = verify_token(token)
        assert payload["fresh"] is True

    def test_non_fresh_token_by_default(self):
        token = create_access_token({"sub": "testuser"})
        payload = verify_token(token)
        assert payload["fresh"] is False

    def test_token_contains_iat_and_exp(self):
        token = create_access_token({"sub": "testuser"})
        payload = verify_token(token)
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] > payload["iat"]


# ─── WB-01: Encryption / decryption ───────────────────────────────────────────

class TestEncryption:
    def test_encrypt_produces_different_string(self):
        enc = encrypt_secret("my-totp-secret")
        assert enc != "my-totp-secret"

    def test_decrypt_round_trip(self):
        secret = "JBSWY3DPEHPK3PXP"
        enc = encrypt_secret(secret)
        dec = decrypt_secret(enc)
        assert dec == secret

    def test_encrypt_none_returns_none(self):
        assert encrypt_secret(None) is None

    def test_decrypt_none_returns_none(self):
        assert decrypt_secret(None) is None

    def test_decrypt_garbage_returns_none(self):
        result = decrypt_secret("not-valid-fernet-data")
        assert result is None

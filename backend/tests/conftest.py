"""Test fixtures for DockWatch tests"""
import os
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch

# ── env vars BEFORE any app imports ──────────────────────────────────────────
os.environ["DOCKWATCH_JWT_SECRET"] = "test-secret-1234567890abcdefghijklmnopqrstuvwxyz"
os.environ["DOCKWATCH_CONFIG"] = os.path.join(os.path.dirname(__file__), "test_config.yaml")
os.environ["DOCKWATCH_DB_PATH"] = os.path.join(os.path.dirname(__file__), "test.db")
os.environ.setdefault("DOCKWATCH_ENCRYPTION_KEY", "kHfGG-MaV1S-4TMgOM7DqxFTyUyqogw7h8e981N-e_g=")

# Redirect RSA key dir to a writable temp directory so tests don't need root.
_TEST_KEY_DIR = Path(tempfile.mkdtemp(prefix="dockwatch_test_keys_"))

import app.core.security as _sec
_sec._get_key_dir = lambda: _TEST_KEY_DIR  # type: ignore[method-assign]

# _get_public_key has the path hard-coded too — patch it to use key dir helper.
def _test_get_public_key() -> str:
    pub_file = _TEST_KEY_DIR / "jwt_public.pem"
    if pub_file.exists():
        return pub_file.read_text()
    private_pem, public_pem = _sec._generate_rsa_keys()
    (_TEST_KEY_DIR / "jwt_private.pem").write_text(private_pem)
    pub_file.write_text(public_pem)
    return public_pem

_sec._get_public_key = _test_get_public_key  # type: ignore[method-assign]

from app.main import app


@pytest.fixture
def client():
    """Create TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def auth_token(client):
    """Create authentication token for protected endpoints."""
    # Try to get token (may fail if no user exists)
    response = client.post("/api/auth/token", json={
        "username": "admin",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    return None
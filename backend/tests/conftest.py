"""Test fixtures for DockWatch tests"""
import pytest
from fastapi.testclient import TestClient
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
"""Test fixtures for DockWatch tests"""
import os
import pytest
from fastapi.testclient import TestClient

# Set test environment variables BEFORE any app imports
os.environ["DOCKWATCH_JWT_SECRET"] = "test-secret-1234567890abcdefghijklmnopqrstuvwxyz"
os.environ["DOCKWATCH_CONFIG"] = os.path.join(os.path.dirname(__file__), "test_config.yaml")
os.environ["DOCKWATCH_DB_PATH"] = os.path.join(os.path.dirname(__file__), "test.db")

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
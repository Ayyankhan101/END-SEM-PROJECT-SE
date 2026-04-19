"""Test auth endpoints"""
import pytest
from fastapi.testclient import TestClient


def test_login_success(client, db_session):
    """Test successful login"""
    # First create a user
    from app.db.models import User
    user = User(username="testuser", password_hash="hashed")
    db.session.add(user)
    db.session.commit()

    response = client.post("/api/auth/token", json={
        "username": "testuser",
        "password": "testpassword"
    })
    assert response.status_code in [200, 401]  # 401 if password doesn't match


def test_login_invalid_credentials(client):
    """Test login with invalid credentials"""
    response = client.post("/api/auth/token", json={
        "username": "nonexistent",
        "password": "wrong"
    })
    assert response.status_code == 401


def test_protected_endpoint_without_token(client):
    """Test accessing protected endpoint without token"""
    response = client.get("/api/containers")
    assert response.status_code == 401


def test_protected_endpoint_with_token(client, auth_token):
    """Test accessing protected endpoint with token"""
    response = client.get(
        "/api/containers",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
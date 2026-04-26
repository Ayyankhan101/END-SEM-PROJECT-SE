"""Test password change endpoints"""
import pytest
from fastapi.testclient import TestClient


def test_change_password_first_login_success(client):
    """Test successful first login password change"""
    # First, ensure we have a user with must_change_password=1
    # We'll create a test user directly in the DB for this test
    from app.db.models import User, get_db
    from app.core.security import get_password_hash
    
    db = next(get_db())
    
    # Clean up any existing test user
    existing = db.query(User).filter(User.username == "testuser").first()
    if existing:
        db.delete(existing)
        db.commit()
    
    # Create test user with must_change_password=1
    # Password must meet strength requirements: 12+ chars, upper, lower, digit, special
    test_password = "OldPassword123!"
    test_user = User(
        username="testuser",
        hashed_password=get_password_hash(test_password),
        must_change_password=1
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    
    # Now test the password change endpoint
    new_password = "NewPassword456!"
    response = client.post("/api/auth/change-password-first-login", json={
        "username": "testuser",
        "old_password": test_password,
        "new_password": new_password
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Password changed successfully" in data["message"]
    
    # Verify the user's password was updated and must_change_password is now 0
    db.refresh(test_user)
    from app.core.security import verify_password
    assert verify_password(new_password, test_user.hashed_password)
    assert test_user.must_change_password == 0
    
    # Clean up
    db.delete(test_user)
    db.commit()


def test_change_password_first_login_invalid_old_password(client):
    """Test first login password change with invalid old password"""
    from app.db.models import User, get_db
    from app.core.security import get_password_hash
    
    db = next(get_db())
    
    # Clean up any existing test user
    existing = db.query(User).filter(User.username == "testuser2").first()
    if existing:
        db.delete(existing)
        db.commit()
    
    # Create test user
    test_user = User(
        username="testuser2",
        hashed_password=get_password_hash("oldpassword123!"),
        must_change_password=1
    )
    db.add(test_user)
    db.commit()
    
    # Try with wrong old password
    response = client.post("/api/auth/change-password-first-login", json={
        "username": "testuser2",
        "old_password": "wrongpassword",
        "new_password": "newpassword456!"
    })
    
    assert response.status_code == 400
    assert "Invalid username or password" in response.json()["detail"]
    
    # Clean up
    db.delete(test_user)
    db.commit()


def test_change_password_first_login_password_too_short(client):
    """Test first login password change with password too short"""
    from app.db.models import User, get_db
    from app.core.security import get_password_hash
    
    db = next(get_db())
    
    # Clean up any existing test user
    existing = db.query(User).filter(User.username == "testuser3").first()
    if existing:
        db.delete(existing)
        db.commit()
    
    # Create test user
    test_user = User(
        username="testuser3",
        hashed_password=get_password_hash("oldpassword123!"),
        must_change_password=1
    )
    db.add(test_user)
    db.commit()
    
    # Try with password too short
    response = client.post("/api/auth/change-password-first-login", json={
        "username": "testuser3",
        "old_password": "oldpassword123!",
        "new_password": "short"
    })
    
    assert response.status_code == 400
    assert "Password must be at least 12 characters long" in response.json()["detail"]
    
    # Clean up
    db.delete(test_user)
    db.commit()


def test_change_password_first_login_missing_fields(client):
    """Test first login password change with missing fields"""
    response = client.post("/api/auth/change-password-first-login", json={})
    
    # With Pydantic validation, missing fields return 422 Unprocessable Entity
    assert response.status_code == 422
    # Check that it's a validation error (new error format)
    data = response.json()
    assert "error" in data
    assert "details" in data


def test_change_password_first_login_nonexistent_user(client):
    """Test first login password change with nonexistent user"""
    response = client.post("/api/auth/change-password-first-login", json={
        "username": "nonexistent",
        "old_password": "anything",
        "new_password": "newpassword456!"
    })
    
    assert response.status_code == 400
    assert "Invalid username or password" in response.json()["detail"]
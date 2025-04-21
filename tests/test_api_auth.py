# ---------- tests/test_api_auth.py ----------
import pytest
from fastapi.testclient import TestClient


def test_login_valid_credentials(client: TestClient, test_user):
    """Test login with valid credentials."""
    login_data = {
        "username": test_user.email,
        "password": "testpassword",
    }

    response = client.post("/token", data=login_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient):
    """Test login with invalid credentials."""
    # Wrong password
    login_data = {
        "username": "test@example.com",
        "password": "wrongpassword",
    }

    response = client.post("/token", data=login_data)
    assert response.status_code == 401

    # Non-existent user
    login_data = {
        "username": "nonexistent@example.com",
        "password": "testpassword",
    }

    response = client.post("/token", data=login_data)
    assert response.status_code == 401


def test_user_registration(client: TestClient):
    """Test user registration."""
    user_data = {
        "email": "newuser@example.com",
        "password": "password123",
    }

    response = client.post("/users/", json=user_data)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data

    # Try to register with the same email
    response = client.post("/users/", json=user_data)
    assert response.status_code == 400  # Should fail with conflict


def test_get_current_user(client: TestClient, user_token_headers):
    """Test getting the current user with a valid token."""
    response = client.get("/users/me/", headers=user_token_headers)

    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    assert "id" in data


def test_access_without_token(client: TestClient):
    """Test accessing protected endpoints without a token."""
    # Try accessing endpoint without a token
    response = client.get("/users/me/")
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    # Test another protected endpoint
    response = client.get("/users/me/todos/")
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"

# ---------- tests/test_api_admin.py ----------
import pytest
from fastapi.testclient import TestClient


def test_admin_get_all_users(client: TestClient, admin_token_headers, test_user):
    """Test admin endpoint to get all users."""
    response = client.get("/users/", headers=admin_token_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # At least test_user and test_admin

    # Check if our test user is in the list
    assert any(user["id"] == test_user.id for user in data)

    # Regular user should not have access
    response = client.get("/users/", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401


def test_admin_get_user_by_id(client: TestClient, admin_token_headers, test_user):
    """Test admin endpoint to get a specific user by ID."""
    response = client.get(f"/users/{test_user.id}", headers=admin_token_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert "todos" in data  # Should include todos


def test_regular_user_cannot_access_admin_endpoints(client: TestClient, user_token_headers):
    """Test that regular users cannot access admin endpoints."""
    # Try to get all users
    response = client.get("/users/", headers=user_token_headers)
    assert response.status_code == 403

    # Try to get a user by ID
    response = client.get("/users/1", headers=user_token_headers)
    assert response.status_code == 403

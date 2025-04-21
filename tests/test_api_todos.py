# ---------- tests/test_api_todos.py ----------
import pytest
from fastapi.testclient import TestClient


def test_create_todo(client: TestClient, user_token_headers):
    """Test creating a todo."""
    todo_data = {
        "title": "New API Todo",
        "description": "This is a todo created via API"
    }

    response = client.post("/todos/", json=todo_data, headers=user_token_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New API Todo"
    assert data["description"] == "This is a todo created via API"
    assert data["is_done"] is False
    assert "id" in data


def test_get_todos_for_user(client: TestClient, user_token_headers, test_todo):
    """Test getting todos for the current user."""
    response = client.get("/users/me/todos/", headers=user_token_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(todo["id"] == test_todo.id for todo in data)


def test_get_specific_todo(client: TestClient, user_token_headers, test_todo):
    """Test getting a specific todo by ID."""
    response = client.get(f"/todos/{test_todo.id}", headers=user_token_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_todo.id
    assert data["title"] == test_todo.title


def test_update_todo(client: TestClient, user_token_headers, test_todo):
    """Test updating a todo."""
    update_data = {
        "title": "Updated API Todo",
        "is_done": True
    }

    response = client.put(f"/todos/{test_todo.id}", json=update_data, headers=user_token_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_todo.id
    assert data["title"] == "Updated API Todo"
    assert data["is_done"] is True

    # Verify the update persisted
    response = client.get(f"/todos/{test_todo.id}", headers=user_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated API Todo"
    assert data["is_done"] is True


def test_delete_todo(client: TestClient, user_token_headers, test_todo):
    """Test deleting a todo."""
    response = client.delete(f"/todos/{test_todo.id}", headers=user_token_headers)

    assert response.status_code == 204

    # Verify the todo is gone
    response = client.get(f"/todos/{test_todo.id}", headers=user_token_headers)
    assert response.status_code == 404


def test_cannot_access_others_todo(client: TestClient, session, user_token_headers, test_admin):
    """Test that a user cannot access another user's todo."""
    # Create a todo owned by the admin
    from backend.repository import TodoRepository
    from backend.schemas import TodoCreate

    todo_repo = TodoRepository(session)
    admin_todo = todo_repo.create(
        TodoCreate(title="Admin's Todo"),
        test_admin.id
    )

    # Try to access with regular user token
    response = client.get(f"/todos/{admin_todo.id}", headers=user_token_headers)
    assert response.status_code == 404

    # Try to update
    response = client.put(
        f"/todos/{admin_todo.id}",
        json={"title": "Hacked Todo"},
        headers=user_token_headers
    )
    assert response.status_code == 404

    # Try to delete
    response = client.delete(f"/todos/{admin_todo.id}", headers=user_token_headers)
    assert response.status_code == 404

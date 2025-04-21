# ---------- tests/test_repositories.py ----------
import pytest
from sqlmodel import Session
from fastapi import HTTPException

from backend.repository import UserRepository, TodoRepository
from backend.schemas import UserCreate, UserUpdate, TodoCreate, TodoUpdate


def test_user_repository_create(session: Session):
    """Test creating a user."""
    user_repo = UserRepository(session)
    user_create = UserCreate(
        email="newuser@example.com",
        password="testpassword"
    )

    user = user_repo.create(user_create)

    assert user.id is not None
    assert user.email == "newuser@example.com"
    assert user.hashed_password != "testpassword"  # Password should be hashed
    assert user.is_active is True


def test_user_repository_get_by_email(session: Session, test_user):
    """Test getting a user by email."""
    user_repo = UserRepository(session)

    # Should find existing user
    user = user_repo.get_by_email(test_user.email)
    assert user is not None
    assert user.id == test_user.id

    # Should return None for non-existent user
    user = user_repo.get_by_email("nonexistent@example.com")
    assert user is None


def test_user_repository_update(session: Session, test_user):
    """Test updating a user."""
    user_repo = UserRepository(session)

    # Update email only
    update_data = UserUpdate(email="updated@example.com")
    updated_user = user_repo.update(test_user.id, update_data)

    assert updated_user is not None
    assert updated_user.email == "updated@example.com"

    # Update password
    old_hash = updated_user.hashed_password
    update_data = UserUpdate(password="newpassword")
    updated_user = user_repo.update(test_user.id, update_data)

    assert updated_user is not None
    assert updated_user.hashed_password != old_hash


def test_todo_repository_create(session: Session, test_user):
    """Test creating a todo."""
    todo_repo = TodoRepository(session)
    todo_create = TodoCreate(
        title="New Todo",
        description="This is a new todo"
    )

    todo = todo_repo.create(todo_create, test_user.id)

    assert todo.id is not None
    assert todo.title == "New Todo"
    assert todo.description == "This is a new todo"
    assert todo.is_done is False
    assert todo.owner_id == test_user.id


def test_todo_repository_get_by_owner(session: Session, test_user, test_todo):
    """Test getting todos by owner."""
    todo_repo = TodoRepository(session)

    # Create another todo for the same user
    todo_create = TodoCreate(title="Another Todo")
    todo_repo.create(todo_create, test_user.id)

    # Should find both todos
    todos = todo_repo.get_by_owner(test_user.id)
    assert len(todos) == 2
    assert all(todo.owner_id == test_user.id for todo in todos)


def test_todo_repository_update(session: Session, test_user, test_todo):
    """Test updating a todo."""
    todo_repo = TodoRepository(session)

    # Update title and mark as done
    update_data = TodoUpdate(title="Updated Todo", is_done=True)
    updated_todo = todo_repo.update(test_todo.id, update_data, test_user.id)

    assert updated_todo is not None
    assert updated_todo.title == "Updated Todo"
    assert updated_todo.is_done is True

    # Partial update (only description)
    update_data = TodoUpdate(description="Updated description")
    updated_todo = todo_repo.update(test_todo.id, update_data, test_user.id)

    assert updated_todo is not None
    assert updated_todo.title == "Updated Todo"  # Should remain unchanged
    assert updated_todo.description == "Updated description"
    assert updated_todo.is_done is True  # Should remain unchanged


def test_todo_repository_delete(session: Session, test_user, test_todo):
    """Test deleting a todo."""
    todo_repo = TodoRepository(session)

    # Delete the todo
    deleted_todo = todo_repo.delete_user_todo(test_todo.id, test_user.id)

    assert deleted_todo is not None
    assert deleted_todo.id == test_todo.id

    # Should not be able to find it anymore
    todo = todo_repo.get_user_todo(test_todo.id, test_user.id)
    assert todo is None

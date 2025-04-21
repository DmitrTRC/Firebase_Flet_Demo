# ---------- tests/conftest.py ----------
import os
import pytest
from datetime import timedelta
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

# Import backend.main explicitly (not just main)
from backend.main import app
from backend.models import User, Todo
from backend.security import get_password_hash, create_access_token
from backend.schemas import UserCreate, TodoCreate
from backend.repository import UserRepository, TodoRepository

# Load environment variables from .env file
load_dotenv()

# Use in-memory SQLite for testing
@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(engine, session):
    # Dependencies override
    def get_test_session():
        yield session

    app.dependency_overrides = {}
    from backend.database import get_session
    app.dependency_overrides[get_session] = get_test_session

    yield TestClient(app)

    # Restore original settings
    app.dependency_overrides = {}


@pytest.fixture(name="test_user")
def test_user_fixture(session):
    """Create a test user for testing."""
    user_repo = UserRepository(session)

    # Check if test user already exists
    user = user_repo.get_by_email("test@example.com")

    if not user:
        user_create = UserCreate(
            email="test@example.com",
            password="testpassword"
        )
        user = user_repo.create(user_create)

    return user


@pytest.fixture(name="test_admin")
def test_admin_fixture(session):
    """Create a test admin user for testing."""
    user_repo = UserRepository(session)

    # Check if admin user already exists
    admin = user_repo.get_by_email("admin@example.com")

    if not admin:
        admin_create = UserCreate(
            email="admin@example.com",
            password="adminpassword",
            is_admin=True
        )
        admin = user_repo.create(admin_create)

    return admin


@pytest.fixture(name="test_todo")
def test_todo_fixture(session, test_user):
    """Create a test todo for testing."""
    todo_repo = TodoRepository(session)

    todo_create = TodoCreate(
        title="Test Todo",
        description="This is a test todo",
        is_done=False
    )

    todo = todo_repo.create(todo_create, owner_id=test_user.id)
    return todo


@pytest.fixture(name="user_token_headers")
def user_token_headers_fixture(test_user):
    """Create authorization headers with user JWT token."""
    access_token = create_access_token(
        data={"sub": test_user.email},
        expires_delta=timedelta(minutes=30)
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(name="admin_token_headers")
def admin_token_headers_fixture(test_admin):
    """Create authorization headers with admin JWT token."""
    access_token = create_access_token(
        data={"sub": test_admin.email},
        expires_delta=timedelta(minutes=30)
    )
    return {"Authorization": f"Bearer {access_token}"}

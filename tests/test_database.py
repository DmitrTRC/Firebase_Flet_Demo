# ---------- tests/test_database.py ----------
import pytest
from sqlmodel import Session
from backend.database import init_db, get_db_session

# ---------- 2. UPDATE: tests/test_database.py ----------
def test_init_db(engine):
    """Test database initialization."""
    init_db()

    # Check if we can create a session
    with Session(engine) as session:
        # Use text() for raw SQL queries
        from sqlalchemy import text
        result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]

        # Check that our main tables exist
        assert "user" in tables
        assert "todo" in tables


def test_get_db_session_context_manager(engine):
    """Test the context manager for database sessions."""
    # Import text for raw SQL
    from sqlalchemy import text

    # Test successful transaction
    with get_db_session() as session:
        # Do something that works
        result = session.execute(text("SELECT 1")).scalar_one()
        assert result == 1

    # Test transaction rollback on exception
    try:
        with get_db_session() as session:
            # First do something valid
            session.execute(text("SELECT 1"))
            # Then do something that will fail
            raise ValueError("Test exception")
    except ValueError:
        # Exception should propagate, and transaction should be rolled back
        pass

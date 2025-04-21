# ---------- 4. NEXT UPDATE: backend/database.py ----------
import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session

# Load environment variables from .env file
load_dotenv()

# Get database URL from environment variables with a fallback
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# Create database engine with logging
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)


def init_db() -> None:
    """Initialize database by creating all tables."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency for getting a database session."""
    with Session(engine) as session:
        yield session


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for getting a database session."""
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

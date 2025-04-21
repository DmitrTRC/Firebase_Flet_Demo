# ---------- 2. THEN UPDATE: backend/models.py (add verify_password method) ----------
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import Field, Relationship, SQLModel

# Avoid circular imports
if TYPE_CHECKING:
    from .schemas import TodoRead


class UserBase(SQLModel):
    """Base model for User with common fields."""
    email: str = Field(index=True, unique=True)
    hashed_password: str = Field()
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)


class User(UserBase, table=True):
    """User DB model for storing in the database."""
    id: Optional[int] = Field(default=None, primary_key=True)
    todos: List["Todo"] = Relationship(back_populates="owner")

    def verify_password(self, password: str) -> bool:
        """Verify password against the stored hash."""
        # Import here to avoid circular imports
        from .security import verify_password
        return verify_password(password, self.hashed_password)


class TodoBase(SQLModel):
    """Base model for Todo with common fields."""
    title: str = Field(index=True)
    description: Optional[str] = Field(default=None, index=True)
    is_done: bool = Field(default=False)


class Todo(TodoBase, table=True):
    """Todo DB model for storing in the database."""
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", nullable=False)
    owner: Optional[User] = Relationship(back_populates="todos")

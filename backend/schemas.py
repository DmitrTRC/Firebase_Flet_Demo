from typing import List, Optional

from pydantic import EmailStr, field_validator

from sqlmodel import SQLModel

from .models import UserBase, TodoBase


class UserCreate(SQLModel):
    """Schema for user creation requests."""
    email: EmailStr
    password: str
    is_active: bool = True
    is_admin: bool = False

    @field_validator("password")
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserRead(SQLModel):
    """Schema for user read responses."""
    id: int
    email: str
    is_active: bool


class UserUpdate(SQLModel):
    """Schema for user update requests."""
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("password")
    def password_min_length(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class TodoCreate(TodoBase):
    """Schema for todo creation requests."""
    pass


class TodoRead(TodoBase):
    """Schema for todo read responses."""
    id: int


class TodoUpdate(SQLModel):
    """Schema for todo update requests."""
    title: Optional[str] = None
    description: Optional[str] = None
    is_done: Optional[bool] = None


class UserReadWithTodos(UserRead):
    """Schema for user read responses with todos included."""
    todos: List[TodoRead] = []


class TodoReadWithOwner(TodoRead):
    """Schema for todo read responses with owner included."""
    owner: UserRead


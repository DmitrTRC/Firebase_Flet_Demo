
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class UserBase(SQLModel):
    email: str = Field(index=True, unique=True)
    hashed_password: str = Field()
    is_active: bool = Field(default=True)


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    todos: List["Todo"] = Relationship(back_populates="owner")


class UserCreate(UserBase):
    password: str # Plain password, will be hashed before saving


class UserRead(SQLModel):
    id: int
    email: str
    is_active: bool


class TodoBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = Field(default=None, index=True)
    is_done: bool = Field(default=False)


class Todo(TodoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", nullable=False)
    owner: Optional[User] = Relationship(back_populates="todos")


class TodoCreate(TodoBase):
    pass


class TodoRead(TodoBase):
    id: int


class TodoUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_done: Optional[bool] = None

# Add relationships to UserRead to include todos if needed
class UserReadWithTodos(UserRead):
    todos: List[TodoRead] = []

# Link TodoRead back to User if needed (circular dependency handling might be required)
class TodoReadWithOwner(TodoRead):
    owner: UserRead


from typing import List, Optional

from sqlmodel import Session, select

from . import models, security

# User CRUD
def get_user(session: Session, user_id: int) -> Optional[models.User]:
    return session.get(models.User, user_id)

def get_user_by_email(session: Session, email: str) -> Optional[models.User]:
    statement = select(models.User).where(models.User.email == email)
    return session.exec(statement).first()

def create_user(session: Session, user: models.UserCreate) -> models.User:
    hashed_password = security.get_password_hash(user.password)
    # Create a User instance without the plain password
    db_user = models.User(email=user.email, hashed_password=hashed_password, is_active=user.is_active)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

# Todo CRUD
def get_todos(session: Session, owner_id: int, skip: int = 0, limit: int = 100) -> List[models.Todo]:
    statement = select(models.Todo).where(models.Todo.owner_id == owner_id).offset(skip).limit(limit)
    return session.exec(statement).all()

def create_user_todo(session: Session, todo: models.TodoCreate, user_id: int) -> models.Todo:
    db_todo = models.Todo(**todo.dict(), owner_id=user_id)
    session.add(db_todo)
    session.commit()
    session.refresh(db_todo)
    return db_todo

def get_todo(session: Session, todo_id: int, owner_id: int) -> Optional[models.Todo]:
    statement = select(models.Todo).where(models.Todo.id == todo_id, models.Todo.owner_id == owner_id)
    return session.exec(statement).first()

def update_todo(session: Session, db_todo: models.Todo, todo_in: models.TodoUpdate) -> models.Todo:
    todo_data = todo_in.dict(exclude_unset=True)
    for key, value in todo_data.items():
        setattr(db_todo, key, value)
    session.add(db_todo)
    session.commit()
    session.refresh(db_todo)
    return db_todo

def delete_todo(session: Session, db_todo: models.Todo):
    session.delete(db_todo)
    session.commit()

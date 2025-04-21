from typing import List, Optional, cast
from sqlmodel import Session, select
from sqlalchemy.sql.selectable import Select
from . import models, security

# User CRUD
def get_user(session: Session, user_id: int) -> Optional[models.User]:
    return session.get(models.User, user_id)

def get_user_by_email(session: Session, email: str) -> Optional[models.User]:
    # Cast the select statement to the expected type
    query = cast(Select, select(models.User).where(models.User.email == email))
    return session.exec(query).first()

def create_user(session: Session, user: models.UserCreate) -> models.User:
    try:
        hashed_password = security.get_password_hash(user.password)
        # Create a User instance without the plain password
        db_user = models.User(email=user.email, hashed_password=hashed_password, is_active=user.is_active)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user
    except Exception as e:
        session.rollback()
        raise ValueError(f"Error creating user: {str(e)}")

# Todo CRUD
def get_todos(session: Session, owner_id: int, skip: int = 0, limit: int = 100) -> List[models.Todo]:
    # Cast the select statement to the expected type
    query = cast(Select, select(models.Todo).where(models.Todo.owner_id == owner_id).offset(skip).limit(limit))
    result = session.exec(query).all()
    # Cast the result to the expected List[models.Todo] type
    return cast(List[models.Todo], result)

def create_user_todo(session: Session, todo: models.TodoCreate, user_id: int) -> models.Todo:
    try:
        # Verify user exists first
        user = session.get(models.User, user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        # Use model_dump() with Pydantic v2+
        todo_data = todo.model_dump()

        db_todo = models.Todo(**todo_data, owner_id=user_id)
        session.add(db_todo)
        session.commit()
        session.refresh(db_todo)
        return db_todo
    except Exception as e:
        session.rollback()
        raise ValueError(f"Error creating todo: {str(e)}")

def get_todo(session: Session, todo_id: int, owner_id: int) -> Optional[models.Todo]:
    # Cast the select statement to the expected type
    query = cast(Select, select(models.Todo).where(models.Todo.id == todo_id, models.Todo.owner_id == owner_id))
    return session.exec(query).first()

def update_todo(session: Session, db_todo: models.Todo, todo_in: models.TodoUpdate) -> models.Todo:
    try:
        # Use model_dump() with Pydantic v2+
        todo_data = todo_in.model_dump(exclude_unset=True)

        # Only update allowed fields
        allowed_fields = {"title", "description", "is_done"}
        for key, value in todo_data.items():
            if key in allowed_fields:
                setattr(db_todo, key, value)

        session.add(db_todo)
        session.commit()
        session.refresh(db_todo)
        return db_todo
    except Exception as e:
        session.rollback()
        raise ValueError(f"Error updating todo: {str(e)}")

def delete_todo(session: Session, db_todo: models.Todo) -> None:
    try:
        session.delete(db_todo)
        session.commit()
    except Exception as e:
        session.rollback()
        raise ValueError(f"Error deleting todo: {str(e)}")

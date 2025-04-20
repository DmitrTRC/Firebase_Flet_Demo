from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr
from sqlmodel import Session

from . import crud, models, security
from .database import get_session, init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Manage application startup and shutdown events.

    This replaces the deprecated @app.on_event("startup") decorator.
    """
    # Startup: Initialize the database
    print("Initializing database...")
    init_db()

    yield

    # Shutdown: Perform cleanup operations
    print("Shutting down application...")


app = FastAPI(
    title="Todo API",
    description="A RESTful API for managing todo items with user authentication",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/token", response_model=security.Token, summary="Create access token")
async def login_for_access_token(
        session: Session = Depends(get_session),
        form_data: OAuth2PasswordRequestForm = Depends()
) -> security.Token:
    """
    Get an access token using email and password.

    - **username**: Email address (OAuth2 form uses username field for email)
    - **password**: User password
    """
    user = crud.get_user_by_email(session=session, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post(
    "/users/",
    response_model=models.UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user"
)
def create_user(
        user: models.UserCreate,
        session: Session = Depends(get_session)
) -> models.UserRead:
    """
    Create a new user account.

    - **email**: Valid email address (must be unique)
    - **password**: Strong password
    """
    db_user = crud.get_user_by_email(session=session, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    created_user = crud.create_user(session=session, user=user)
    return models.UserRead.model_validate(created_user)


@app.get("/users/me/", response_model=models.UserRead, summary="Get current user")
async def read_users_me(
        current_user: models.User = Depends(security.get_current_active_user)
) -> models.UserRead:
    """Get information about the currently authenticated user."""
    return models.UserRead.model_validate(current_user)


@app.get(
    "/users/me/todos/",
    response_model=List[models.TodoRead],
    summary="Get current user's todos"
)
def read_own_todos(
        session: Session = Depends(get_session),
        current_user: models.User = Depends(security.get_current_active_user),
        skip: int = 0,
        limit: int = 100
) -> List[models.TodoRead]:
    """
    Get all todos for the currently authenticated user.

    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return
    """
    todos = crud.get_todos(
        session=session, owner_id=current_user.id, skip=skip, limit=limit
    )
    return [models.TodoRead.model_validate(todo) for todo in todos]


@app.post(
    "/todos/",
    response_model=models.TodoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create new todo"
)
def create_todo(
        todo: models.TodoCreate,
        session: Session = Depends(get_session),
        current_user: models.User = Depends(security.get_current_active_user)
) -> models.TodoRead:
    """
    Create a new todo item for the current user.

    - **title**: Title of the todo item (required)
    - **description**: Optional detailed description
    - **is_done**: Completion status (defaults to False)
    """
    created_todo = crud.create_user_todo(
        session=session, todo=todo, user_id=current_user.id
    )
    return models.TodoRead.model_validate(created_todo)


@app.get(
    "/todos/{todo_id}",
    response_model=models.TodoReadWithOwner,
    summary="Get todo by ID"
)
def read_todo(
        todo_id: int,
        session: Session = Depends(get_session),
        current_user: models.User = Depends(security.get_current_active_user)
) -> models.TodoReadWithOwner:
    """
    Get a specific todo item by its ID.
    Returns not only the todo but also info about its owner.

    - **todo_id**: The ID of the todo item to retrieve
    """
    db_todo = crud.get_todo(session=session, todo_id=todo_id, owner_id=current_user.id)
    if db_todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )

    # Make sure the relationship is loaded
    todo_read = models.TodoRead.model_validate(db_todo)
    owner_read = models.UserRead.model_validate(current_user)

    return models.TodoReadWithOwner(
        id=todo_read.id,
        title=todo_read.title,
        description=todo_read.description,
        is_done=todo_read.is_done,
        owner=owner_read
    )


@app.put(
    "/todos/{todo_id}",
    response_model=models.TodoRead,
    summary="Update todo"
)
def update_todo_item(
        todo_id: int,
        todo_in: models.TodoUpdate,
        session: Session = Depends(get_session),
        current_user: models.User = Depends(security.get_current_active_user)
) -> models.TodoRead:
    """
    Update a todo item's details.

    - **todo_id**: The ID of the todo item to update
    - **todo_in**: The new todo data (only fields to update need to be included)
    """
    db_todo = crud.get_todo(session=session, todo_id=todo_id, owner_id=current_user.id)
    if db_todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )

    updated_todo = crud.update_todo(session=session, db_todo=db_todo, todo_in=todo_in)
    return models.TodoRead.model_validate(updated_todo)


@app.delete(
    "/todos/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete todo"
)
def delete_todo_item(
        todo_id: int,
        session: Session = Depends(get_session),
        current_user: models.User = Depends(security.get_current_active_user)
) -> None:
    """
    Delete a todo item.

    - **todo_id**: The ID of the todo item to delete
    """
    db_todo = crud.get_todo(session=session, todo_id=todo_id, owner_id=current_user.id)
    if db_todo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )

    crud.delete_todo(session=session, db_todo=db_todo)

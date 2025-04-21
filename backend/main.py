# ---------- 8. THEN UPDATE: backend/main.py ----------
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import List, Optional, Annotated

from fastapi import Depends, FastAPI, HTTPException, status, Path, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr
from sqlmodel import Session

from logger import logger
from .database import get_session, init_db
from .models import User
from .repository import UserRepository, TodoRepository
from .schemas import (
    UserCreate, UserRead, UserUpdate, UserReadWithTodos,
    TodoCreate, TodoRead, TodoUpdate, TodoReadWithOwner
)
from .security import (
    Token, ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token,
    get_current_active_user, get_admin_user
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown events.
    """
    # Startup: Initialize the database
    logger.info("Initializing database...")
    init_db()
    yield
    # Shutdown: Perform cleanup operations
    logger.info("Shutting down application...")


app = FastAPI(
    title="Todo API",
    description="A RESTful API for managing todo items with user authentication",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Authentication endpoints
@app.post("/token", response_model=Token, summary="Create access token")
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        session: Annotated[Session, Depends(get_session)]
) -> Token:
    """
    Get an access token using email and password.
    """
    logger.info(f"Login attempt for user: {form_data.username}")

    user_repo = UserRepository(session)
    user = user_repo.get_by_email(form_data.username)

    if not user or not user.verify_password(form_data.password):
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )

    logger.info(f"Successful login for user: {form_data.username}")
    return Token(access_token=access_token, token_type="bearer")


# User endpoints
@app.post("/users/", response_model=UserRead, status_code=status.HTTP_201_CREATED, summary="Create new user")
async def create_user(
        user: Annotated[UserCreate, Body(...)],
        session: Annotated[Session, Depends(get_session)]
) -> UserRead:
    """
    Create a new user.
    """
    try:
        user_repo = UserRepository(session)
        db_user = user_repo.create(user)
        return db_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/users/me/", response_model=UserRead, summary="Get current user")
async def read_users_me(
        current_user: Annotated[User, Depends(get_current_active_user)]
) -> UserRead:
    """
    Get current authenticated user.
    """
    return current_user


@app.get("/users/me/todos/", response_model=List[TodoRead], summary="Get current user todos")
async def read_users_me_todos(
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[Session, Depends(get_session)],
        skip: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 100
) -> List[TodoRead]:
    """
    Get todos for the current authenticated user.
    """
    todo_repo = TodoRepository(session)
    return todo_repo.get_by_owner(current_user.id, skip, limit)


@app.put("/users/me/", response_model=UserRead, summary="Update current user")
async def update_user_me(
        user_update: Annotated[UserUpdate, Body(...)],
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[Session, Depends(get_session)]
) -> UserRead:
    """
    Update current authenticated user.
    """
    try:
        user_repo = UserRepository(session)
        updated_user = user_repo.update(current_user.id, user_update)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return updated_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Admin-only user endpoints
@app.get("/users/", response_model=List[UserRead], summary="Get all users (admin only)")
async def read_users(
        admin_user: Annotated[User, Depends(get_admin_user)],
        session: Annotated[Session, Depends(get_session)],
        skip: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 100
) -> List[UserRead]:
    """
    Get all users. Admin access required.
    """
    user_repo = UserRepository(session)
    return user_repo.get_multi(skip, limit)


@app.get("/users/{user_id}", response_model=UserReadWithTodos, summary="Get user by ID (admin only)")
async def read_user(
        user_id: Annotated[int, Path(...)],
        admin_user: Annotated[User, Depends(get_admin_user)],
        session: Annotated[Session, Depends(get_session)]
) -> UserReadWithTodos:
    """
    Get user by ID with their todos. Admin access required.
    """
    user_repo = UserRepository(session)
    db_user = user_repo.get(user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return db_user


# Todo endpoints
@app.post("/todos/", response_model=TodoRead, status_code=status.HTTP_201_CREATED, summary="Create todo")
async def create_todo(
        todo: Annotated[TodoCreate, Body(...)],
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[Session, Depends(get_session)]
) -> TodoRead:
    """
    Create a new todo for current user.
    """
    try:
        todo_repo = TodoRepository(session)
        return todo_repo.create(todo, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/todos/{todo_id}", response_model=TodoRead, summary="Get todo by ID")
async def read_todo(
        todo_id: Annotated[int, Path(...)],
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[Session, Depends(get_session)]
) -> TodoRead:
    """
    Get a specific todo owned by current user.
    """
    todo_repo = TodoRepository(session)
    db_todo = todo_repo.get_user_todo(todo_id, current_user.id)
    if not db_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    return db_todo


@app.put("/todos/{todo_id}", response_model=TodoRead, summary="Update todo")
async def update_todo(
        todo_id: Annotated[int, Path(...)],
        todo_update: Annotated[TodoUpdate, Body(...)],
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[Session, Depends(get_session)]
) -> TodoRead:
    """
    Update a specific todo owned by current user.
    """
    try:
        todo_repo = TodoRepository(session)
        db_todo = todo_repo.update(todo_id, todo_update, current_user.id)
        if not db_todo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Todo not found"
            )
        return db_todo
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete todo")
async def delete_todo(
        todo_id: Annotated[int, Path(...)],
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[Session, Depends(get_session)]
) -> None:
    """
    Delete a specific todo owned by current user.
    """
    try:
        todo_repo = TodoRepository(session)
        db_todo = todo_repo.delete_user_todo(todo_id, current_user.id)
        if not db_todo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Todo not found"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

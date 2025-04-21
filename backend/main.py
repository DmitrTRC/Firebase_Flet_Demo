from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr
from sqlmodel import Session

from logger import logger
from . import crud, models, security
from .database import get_session, init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Manage application startup and shutdown events.

    This replaces the deprecated @app.on_event("startup") decorator.
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


@app.post("/token", response_model=security.Token, summary="Create access token")
async def login_for_access_token(
        session: Session = Depends(get_session),
        form_data: OAuth2PasswordRequestForm = Depends()
) -> dict[str, str]:
    """
    Get an access token using email and password.

    - **username**: Email address (OAuth2 form uses username field for email)
    - **password**: User password
    """
    logger.info(f"Login attempt for user: {form_data.username}")
    user = crud.get_user_by_email(session=session, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    logger.info(f"Successful login for user: {form_data.username}")
    return {"access_token": access_token, "token_type": "bearer"}

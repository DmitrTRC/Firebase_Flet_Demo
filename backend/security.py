import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlmodel import Session

from . import crud, models
from .database import get_session

load_dotenv()

# Configuration loaded from environment variables with fallback to a generated key
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Generate a secure random key instead of raising an error
    SECRET_KEY = secrets.token_hex(32)
    print("WARNING: No SECRET_KEY found in environment. Using a generated key.")
    print("For production, set a SECRET_KEY in your .env file.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
DEBUG_ADMIN_EMAIL = os.getenv("DEBUG_ADMIN_EMAIL", "admin@example.com")

if DEBUG_MODE:
    print("WARNING: DEBUG_MODE is enabled. Authentication will be bypassed.")
    print("This should NEVER be enabled in production environments.")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=not DEBUG_MODE)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(session: Session = Depends(get_session), token: str = Depends(oauth2_scheme)) -> models.User:
    # If debug mode is enabled and token is None, use the debug admin user
    if DEBUG_MODE and token is None:
        # Try to get the admin user, create if doesn't exist
        admin_user = crud.get_user_by_email(session=session, email=DEBUG_ADMIN_EMAIL)
        if not admin_user:
            # Create a default admin user if it doesn't exist
            admin_password = get_password_hash("admin")
            admin_user = crud.create_user(
                session=session,
                user=models.UserCreate(
                    email=DEBUG_ADMIN_EMAIL,
                    password=admin_password,
                    is_active=True,
                    is_admin=True
                )
            )
            print(f"Created debug admin user: {DEBUG_ADMIN_EMAIL}")
        return admin_user

    # Normal authentication flow
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_email(session=session, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

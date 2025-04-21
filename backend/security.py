# ---------- UPDATE: backend/security.py ----------
import os
from typing import Annotated, Optional
from datetime import datetime, timedelta, UTC  # Add UTC import
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session

from .database import get_session
from .models import User

# JWT settings
SECRET_KEY = "your-secret-key-replace-in-production"  # Replace in production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 token URL
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    auto_error=True  # Set to False if you want endpoints to be accessible without token
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(
        data: dict,
        expires_delta: Optional[timedelta] = None
) -> str:
    """Create a new JWT token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
        token: Annotated[str, Depends(oauth2_scheme)],
        session: Annotated[Session, Depends(get_session)]
) -> User:
    """Get the current user from JWT token."""
    # Check for debug mode
    debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

    if debug_mode:
        # In debug mode, return a default admin user
        # First check if user exists
        from sqlmodel import select
        from .models import User

        admin_query = select(User).where(User.email == "admin@example.com")
        admin = session.exec(admin_query).first()

        if not admin:
            # Create a debug admin user
            admin = User(
                email="admin@example.com",
                hashed_password=get_password_hash("adminpassword"),
                is_active=True,
                is_admin=True
            )
            session.add(admin)
            session.commit()
            session.refresh(admin)

        return admin

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
    except JWTError:
        raise credentials_exception

    # Get user from database
    from sqlmodel import select
    from .models import User

    user_query = select(User).where(User.email == email)
    user = session.exec(user_query).first()

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
        current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_admin_user(
        current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """Verify the current user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


# Token data model
from pydantic import BaseModel

class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str

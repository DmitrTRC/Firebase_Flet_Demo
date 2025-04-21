# ---------- tests/test_security.py ----------
import pytest
from datetime import timedelta
from jose import jwt
from backend.security import verify_password, get_password_hash, create_access_token, ALGORITHM, SECRET_KEY


def test_password_hash():
    """Test password hashing and verification."""
    password = "testpassword"
    hashed = get_password_hash(password)

    # Hashed password should be different from original
    assert hashed != password

    # Verification should work
    assert verify_password(password, hashed)

    # Wrong password should fail
    assert not verify_password("wrongpassword", hashed)


def test_create_access_token():
    """Test JWT token creation."""
    data = {"sub": "test@example.com"}
    expires_delta = timedelta(minutes=30)

    token = create_access_token(data, expires_delta)

    # Token should be a string
    assert isinstance(token, str)

    # Token should be decodable with our secret key
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    # Token should contain our data
    assert decoded["sub"] == "test@example.com"

    # Token should have an expiration time
    assert "exp" in decoded

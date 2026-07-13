from __future__ import annotations
import os
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ice_shared.settings import settings
from ice_api.models import User
from ice_shared.db import get_session

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# JWT config - use the canonical settings.jwt_secret (set via .env / JWT_SECRET).
# This is the single source of truth so sign (create_access_token) and verify
# (get_current_user, /refresh) use the same key. Do NOT read JWT_SECRET_KEY
# from os.getenv here: main.py's load_dotenv points at a non-existent path
# inside the Docker container, which would fall back to a divergent default
# and break signature verification.
SECRET_KEY = settings.jwt_secret
ALGORITHM = settings.jwt_algorithm

# Try to get values from settings, use fallback if not defined
def get_access_token_expire_minutes():
    return getattr(settings, 'jwt_access_ttl_min', 60)

def get_refresh_token_expire_days():
    return getattr(settings, 'jwt_refresh_ttl_days', 7)

def generate_verification_code() -> str:
    """Generate a 6-digit numeric code."""
    return ''.join(secrets.choice(string.digits) for _ in range(6))

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=get_access_token_expire_minutes()))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(days=get_refresh_token_expire_days())
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_raw = payload.get("sub")
        if user_id_raw is None:
            raise credentials_exception
        # Reject refresh tokens used as access tokens (RFC-style type claim).
        if payload.get("type") != "access":
            raise credentials_exception
        # "sub" must be a string per JWT RFC 7519; python-jose enforces this on
        # decode. Cast back to int for the ORM lookup (User.id is Integer).
        user_id = int(user_id_raw)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception
    
    stmt = select(User).where(User.id == user_id, User.is_active == True)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

def is_valid_email(email: str) -> bool:
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def sanitize_input(text: str) -> str:
    """Remove special characters to prevent injection."""
    return ''.join(c for c in text if c.isalnum() or c in ' @.-_')  
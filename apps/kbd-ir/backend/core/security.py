"""Security helpers for authentication and password hashing."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

ALGORITHM = "HS256"
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_context.verify(password, hashed_password)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject: str = payload.get("sub")
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return subject
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc

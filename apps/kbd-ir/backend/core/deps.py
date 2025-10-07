"""FastAPI dependencies for authentication and database access."""
from __future__ import annotations

from typing import Generator, Iterable, Sequence
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..models import Circle, CircleScope, Role, User
from .database import SessionLocal
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/kbd_ir/auth/login")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    user_id = decode_access_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return user


def require_roles(allowed_roles: Sequence[Role]):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return dependency


def ensure_circle_access(
    user: User,
    tournament_scope: CircleScope,
    allow_joint: bool = True,
) -> None:
    """Ensure that a user can access a tournament with the given scope."""

    if user.role == Role.SUPERADMIN:
        return
    if tournament_scope == CircleScope.JOINT and allow_joint:
        if user.role in {Role.KBM_USER, Role.KBM_ADMIN, Role.BBD_USER, Role.BBD_ADMIN}:
            return
    circle_map = {
        Role.KBM_ADMIN: Circle.KBM,
        Role.KBM_USER: Circle.KBM,
        Role.BBD_ADMIN: Circle.BBD,
        Role.BBD_USER: Circle.BBD,
    }
    target_circle = circle_map.get(user.role)
    if target_circle is None or CircleScope(target_circle.value) != tournament_scope:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tournament not accessible")

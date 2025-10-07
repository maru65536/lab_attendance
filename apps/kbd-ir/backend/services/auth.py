"""Authentication service layer."""
from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.email import send_password_reset_email
from ..core.security import create_access_token, hash_password, verify_password
from ..models import Circle, PasswordResetToken, Role, User


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def signup(self, email: str, password: str, display_name: str, circle: Circle) -> User:
        if self.db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        user = User(
            id=str(uuid4()),
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
            circle=circle,
            role=self._initial_role(circle),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def login(self, email: str, password: str) -> str:
        user = self.db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User disabled")
        return create_access_token(user.id)

    def request_password_reset(self, email: str, base_url: str) -> None:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return
        token_id = str(uuid4())
        token_secret = str(uuid4())
        hashed = hash_password(token_secret)
        expires_at = datetime.utcnow() + timedelta(minutes=settings.password_reset_expiration_minutes)
        reset = PasswordResetToken(
            id=token_id,
            user_id=user.id,
            token_hash=hashed,
            expires_at=expires_at,
        )
        self.db.add(reset)
        self.db.commit()
        reset_link = f"{base_url}/reset-password?token={token_id}:{token_secret}"
        send_password_reset_email(recipient=user.email, reset_link=reset_link)

    def confirm_password_reset(self, token: str, new_password: str) -> None:
        try:
            token_id, token_secret = token.split(":", 1)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token") from exc

        entry = (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.id == token_id, PasswordResetToken.used_at.is_(None))
            .first()
        )
        if not entry or entry.expires_at < datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")
        if not verify_password(token_secret, entry.token_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
        entry.used_at = datetime.utcnow()
        user = self.db.query(User).filter(User.id == entry.user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
        user.password_hash = hash_password(new_password)
        self.db.commit()

    @staticmethod
    def _initial_role(circle: Circle) -> Role:
        return Role.KBM_USER if circle == Circle.KBM else Role.BBD_USER

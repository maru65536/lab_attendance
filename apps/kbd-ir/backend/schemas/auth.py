"""Authentication-related schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from .common import UserBase
from ..models import Circle


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str
    circle: Circle


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class SessionUser(UserBase):
    pass


class PasswordResetTokenRead(BaseModel):
    id: str
    user_id: str
    expires_at: datetime
    used_at: Optional[datetime]

    class Config:
        orm_mode = True

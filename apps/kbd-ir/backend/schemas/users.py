"""User management schemas."""
from __future__ import annotations

from pydantic import BaseModel

from .common import UserBase
from ..models import Circle, Role


class UserCreate(BaseModel):
    email: str
    display_name: str
    role: Role
    circle: Circle
    password: str


class UserUpdate(BaseModel):
    display_name: str | None = None
    role: Role | None = None
    circle: Circle | None = None
    is_active: bool | None = None


class UserRead(UserBase):
    is_active: bool

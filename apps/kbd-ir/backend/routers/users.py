"""User management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, get_db, require_roles
from ..models import Circle, Role, User
from ..schemas.users import UserRead, UserUpdate

router = APIRouter(prefix="/api/kbd_ir", tags=["users"])

ADMIN_ROLES = [Role.SUPERADMIN, Role.KBM_ADMIN, Role.BBD_ADMIN]


@router.get("/admin/users", response_model=list[UserRead])
def list_users(
    current_user: User = Depends(require_roles(ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if current_user.role == Role.KBM_ADMIN:
        query = query.filter(User.circle == Circle.KBM)
    elif current_user.role == Role.BBD_ADMIN:
        query = query.filter(User.circle == Circle.BBD)
    users = query.order_by(User.created_at.desc()).all()
    return [UserRead.from_orm(user) for user in users]


@router.patch("/admin/users/{user_id}/role", response_model=UserRead)
def update_user_role(
    user_id: str,
    payload: UserUpdate,
    current_user: User = Depends(require_roles(ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if current_user.role == Role.KBM_ADMIN and target.circle != Circle.KBM:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-circle modification forbidden")
    if current_user.role == Role.BBD_ADMIN and target.circle != Circle.BBD:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-circle modification forbidden")

    if payload.role is not None:
        if current_user.role == Role.SUPERADMIN:
            pass
        elif current_user.role == Role.KBM_ADMIN and payload.role not in {Role.KBM_ADMIN, Role.KBM_USER}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign higher role")
        elif current_user.role == Role.BBD_ADMIN and payload.role not in {Role.BBD_ADMIN, Role.BBD_USER}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign higher role")
        target.role = payload.role

    if payload.display_name is not None:
        target.display_name = payload.display_name

    if payload.circle is not None:
        if current_user.role != Role.SUPERADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change circle")
        target.circle = payload.circle
    if payload.is_active is not None:
        target.is_active = payload.is_active

    db.commit()
    db.refresh(target)
    return UserRead.from_orm(target)

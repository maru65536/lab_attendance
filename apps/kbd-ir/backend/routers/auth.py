"""Authentication endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, get_db
from ..models import User
from ..schemas import auth as auth_schemas
from ..services.auth import AuthService

router = APIRouter(prefix="/api/kbd_ir/auth", tags=["auth"])


@router.post("/signup", response_model=auth_schemas.SessionUser)
def signup(payload: auth_schemas.SignupRequest, db: Session = Depends(get_db)):
    service = AuthService(db=db)
    user = service.signup(
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
        circle=payload.circle,
    )
    return auth_schemas.SessionUser.from_orm(user)


@router.post("/login", response_model=auth_schemas.TokenResponse)
def login(payload: auth_schemas.LoginRequest, db: Session = Depends(get_db)):
    service = AuthService(db=db)
    token = service.login(email=payload.email, password=payload.password)
    return auth_schemas.TokenResponse(access_token=token)


@router.post("/password-reset/request")
def password_reset_request(
    payload: auth_schemas.PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    service = AuthService(db=db)
    base_url = str(request.base_url).rstrip("/")
    service.request_password_reset(email=payload.email, base_url=base_url)
    return JSONResponse({"status": "ok"})


@router.post("/password-reset/confirm")
def password_reset_confirm(payload: auth_schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    service = AuthService(db=db)
    service.confirm_password_reset(token=payload.token, new_password=payload.new_password)
    return JSONResponse({"status": "ok"})


@router.get("/me", response_model=auth_schemas.SessionUser)
def me(current_user: User = Depends(get_current_user)):
    return auth_schemas.SessionUser.from_orm(current_user)

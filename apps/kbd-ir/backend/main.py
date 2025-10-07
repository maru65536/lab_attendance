"""FastAPI entrypoint for KBD-IR backend."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.database import engine
from .models import Base
from .routers import auth, metadata, reviews, submissions, tournaments, uploads, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

allow_origins = [origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins if allow_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metadata.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tournaments.router)
app.include_router(submissions.router)
app.include_router(reviews.router)
app.include_router(uploads.router)


@app.get("/")
def root():
    return {"status": "ok", "service": settings.app_name}

"""Database session and engine utilities."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    future=True,
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True))


@contextmanager
def session_scope() -> Generator:
    """Provide a transactional scope around a series of operations."""

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

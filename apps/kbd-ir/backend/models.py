"""Database models for KBD-IR."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Circle(str, enum.Enum):
    KBM = "kbm"
    BBD = "bbd"


class CircleScope(str, enum.Enum):
    KBM = "kbm"
    BBD = "bbd"
    JOINT = "joint"


class Role(str, enum.Enum):
    SUPERADMIN = "superadmin"
    KBM_ADMIN = "kbm-admin"
    BBD_ADMIN = "bbd-admin"
    KBM_USER = "kbm-user"
    BBD_USER = "bbd-user"


class TournamentVisibility(str, enum.Enum):
    PUBLIC = "public"
    OPS_TEST = "ops_test"


class TournamentStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    OPEN = "open"
    CLOSED = "closed"
    ARCHIVED = "archived"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False)
    circle = Column(Enum(Circle), nullable=False)
    display_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    tournaments = relationship("Tournament", back_populates="creator")
    submissions = relationship("ScoreSubmission", back_populates="user")
    reviews = relationship("ScoreReview", back_populates="reviewer")


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    circle_scope = Column(Enum(CircleScope), nullable=False)
    visibility = Column(Enum(TournamentVisibility), nullable=False)
    status = Column(Enum(TournamentStatus), nullable=False, default=TournamentStatus.DRAFT)

    registration_opens = Column(DateTime, nullable=True)
    registration_closes = Column(DateTime, nullable=True)
    event_starts = Column(DateTime, nullable=True)
    event_ends = Column(DateTime, nullable=True)

    score_cap_default = Column(Integer, nullable=False, default=1000000)

    created_by_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    creator = relationship("User", back_populates="tournaments")
    machines = relationship("Machine", back_populates="tournament", cascade="all, delete")


class Machine(Base):
    __tablename__ = "machines"

    id = Column(String, primary_key=True)
    tournament_id = Column(String, ForeignKey("tournaments.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    game_code = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    tournament = relationship("Tournament", back_populates="machines")
    songs = relationship("Song", back_populates="machine", cascade="all, delete")

    __table_args__ = (
        UniqueConstraint("tournament_id", "game_code", name="uq_machine_game_code"),
    )


class Song(Base):
    __tablename__ = "songs"

    id = Column(String, primary_key=True)
    machine_id = Column(String, ForeignKey("machines.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=True)
    difficulty = Column(String, nullable=False)
    score_cap_override = Column(Integer, nullable=True)
    optional_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    machine = relationship("Machine", back_populates="songs")
    submissions = relationship("ScoreSubmission", back_populates="song", cascade="all, delete")

    __table_args__ = (
        UniqueConstraint("machine_id", "title", "difficulty", name="uq_song_unique"),
    )


class ScoreSubmission(Base):
    __tablename__ = "score_submissions"

    id = Column(String, primary_key=True)
    song_id = Column(String, ForeignKey("songs.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    score = Column(Integer, nullable=False)
    photo_key = Column(String, nullable=False)
    review_status = Column(Enum(ReviewStatus), nullable=False, default=ReviewStatus.PENDING)
    review_comment = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    song = relationship("Song", back_populates="submissions")
    user = relationship("User", back_populates="submissions")
    reviews = relationship("ScoreReview", back_populates="submission")

    __table_args__ = (
        UniqueConstraint("song_id", "user_id", name="uq_submission_unique"),
        CheckConstraint("score >= 0", name="ck_score_non_negative"),
    )


class ScoreReview(Base):
    __tablename__ = "score_reviews"

    id = Column(String, primary_key=True)
    submission_id = Column(
        String, ForeignKey("score_submissions.id"), nullable=False, index=True
    )
    reviewer_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    decision = Column(Enum(ReviewStatus), nullable=False)
    comment = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    submission = relationship("ScoreSubmission", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")

    __table_args__ = (
        CheckConstraint("used_at IS NULL OR used_at >= created_at", name="ck_reset_used"),
    )

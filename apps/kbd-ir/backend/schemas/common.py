"""Shared schema components."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from ..models import Circle, CircleScope, ReviewStatus, Role, TournamentStatus, TournamentVisibility


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class UserBase(BaseModel):
    id: str
    email: EmailStr
    display_name: str
    role: Role
    circle: Circle

    class Config:
        orm_mode = True


class TournamentBase(BaseModel):
    id: str
    name: str
    slug: str
    circle_scope: CircleScope
    visibility: TournamentVisibility
    status: TournamentStatus
    score_cap_default: int
    registration_opens: Optional[datetime]
    registration_closes: Optional[datetime]
    event_starts: Optional[datetime]
    event_ends: Optional[datetime]

    class Config:
        orm_mode = True


class MachineBase(BaseModel):
    id: str
    tournament_id: str
    name: str
    game_code: str
    description: Optional[str]

    class Config:
        orm_mode = True


class SongBase(BaseModel):
    id: str
    machine_id: str
    title: str
    artist: Optional[str]
    difficulty: str
    score_cap_override: Optional[int]
    optional_metadata: Optional[dict]

    class Config:
        orm_mode = True


class ScoreSubmissionBase(BaseModel):
    id: str
    song_id: str
    user_id: str
    score: int
    photo_key: str
    review_status: ReviewStatus
    review_comment: Optional[str]
    submitted_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

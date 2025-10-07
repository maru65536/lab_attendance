"""Score submission schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .common import ScoreSubmissionBase


class ScoreSubmissionCreate(BaseModel):
    score: int = Field(ge=0)
    photo_key: str
    comment: Optional[str]


class ScoreSubmissionRead(ScoreSubmissionBase):
    pass


class ScoreSubmissionListItem(ScoreSubmissionBase):
    song_title: str
    machine_name: str
    tournament_name: str

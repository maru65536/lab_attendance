"""Tournament-related schemas."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from .common import MachineBase, SongBase, TournamentBase
from ..models import CircleScope, TournamentStatus, TournamentVisibility


class TournamentCreate(BaseModel):
    name: str
    slug: str
    circle_scope: CircleScope
    visibility: TournamentVisibility
    status: TournamentStatus = TournamentStatus.DRAFT
    registration_opens: Optional[datetime]
    registration_closes: Optional[datetime]
    event_starts: Optional[datetime]
    event_ends: Optional[datetime]
    score_cap_default: int


class TournamentUpdate(BaseModel):
    name: Optional[str]
    visibility: Optional[TournamentVisibility]
    status: Optional[TournamentStatus]
    registration_opens: Optional[datetime]
    registration_closes: Optional[datetime]
    event_starts: Optional[datetime]
    event_ends: Optional[datetime]
    score_cap_default: Optional[int]


class TournamentDetail(TournamentBase):
    machines: List[MachineBase]


class MachineCreate(BaseModel):
    name: str
    game_code: str
    description: Optional[str]


class MachineUpdate(BaseModel):
    name: Optional[str]
    game_code: Optional[str]
    description: Optional[str]


class MachineDetail(MachineBase):
    songs: List[SongBase]


class SongCreate(BaseModel):
    title: str
    artist: Optional[str]
    difficulty: str
    score_cap_override: Optional[int]
    optional_metadata: Optional[dict]


class SongUpdate(BaseModel):
    title: Optional[str]
    artist: Optional[str]
    difficulty: Optional[str]
    score_cap_override: Optional[int]
    optional_metadata: Optional[dict]

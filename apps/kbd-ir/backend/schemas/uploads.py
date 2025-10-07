"""Upload helper schemas."""
from __future__ import annotations

from pydantic import BaseModel


class PresignRequest(BaseModel):
    tournament_slug: str
    song_id: str
    content_type: str = "image/jpeg"


class PresignResponse(BaseModel):
    url: str
    fields: dict

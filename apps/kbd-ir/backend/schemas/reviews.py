"""Review workflow schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from ..models import ReviewStatus


class ReviewDecision(BaseModel):
    decision: ReviewStatus
    comment: Optional[str]

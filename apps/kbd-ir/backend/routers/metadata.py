"""Metadata endpoints for enumerations and health."""
from __future__ import annotations

from fastapi import APIRouter

from ..models import Circle, CircleScope, ReviewStatus, Role, TournamentStatus, TournamentVisibility

router = APIRouter(prefix="/api/kbd_ir", tags=["metadata"])


@router.get("/enums")
def get_enums():
    return {
        "roles": [role.value for role in Role],
        "circles": [circle.value for circle in Circle],
        "circle_scope": [scope.value for scope in CircleScope],
        "tournament_status": [status.value for status in TournamentStatus],
        "tournament_visibility": [visibility.value for visibility in TournamentVisibility],
        "review_status": [status.value for status in ReviewStatus],
    }


@router.get("/health")
def health_check():
    return {"status": "ok"}

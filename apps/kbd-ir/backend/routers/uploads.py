"""Upload helper endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, get_db
from ..core.storage import build_submission_key, generate_presigned_upload
from ..models import Song, Tournament
from ..schemas.uploads import PresignRequest, PresignResponse

router = APIRouter(prefix="/api/kbd_ir", tags=["uploads"])


@router.post("/uploads/presign", response_model=PresignResponse)
def presign_upload(
    payload: PresignRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tournament = db.query(Tournament).filter(Tournament.slug == payload.tournament_slug).first()
    if not tournament:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
    song = db.query(Song).filter(Song.id == payload.song_id).first()
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    key = build_submission_key(tournament_slug=tournament.slug, song_id=song.id, user_id=current_user.id)
    presigned = generate_presigned_upload(key=key, content_type=payload.content_type)
    return PresignResponse(url=presigned["url"], fields=presigned["fields"])

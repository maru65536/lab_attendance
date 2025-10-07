"""Score submission endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, get_db
from ..models import Machine, Role, Song, Tournament, User
from ..schemas import submissions as schemas
from ..services.submissions import ScoreService
from ..services.tournaments import TournamentService

router = APIRouter(prefix="/api/kbd_ir", tags=["submissions"])


@router.get("/tournaments/{tournament_id}/songs", response_model=list[dict])
def list_songs_for_tournament(
    tournament_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t_service = TournamentService(db=db, actor=current_user)
    tournament = t_service.get(tournament_id)
    t_service.ensure_actor_can_view(tournament)

    machines = db.query(Machine).filter(Machine.tournament_id == tournament.id).all()
    response = []
    for machine in machines:
        songs = db.query(Song).filter(Song.machine_id == machine.id).all()
        response.append(
            {
                "machine": {
                    "id": machine.id,
                    "name": machine.name,
                    "game_code": machine.game_code,
                    "description": machine.description,
                },
                "songs": [
                    {
                        "id": song.id,
                        "title": song.title,
                        "artist": song.artist,
                        "difficulty": song.difficulty,
                        "score_cap_override": song.score_cap_override,
                    }
                    for song in songs
                ],
            }
        )
    return response


@router.post("/songs/{song_id}/submissions", response_model=schemas.ScoreSubmissionRead)
def submit_score(
    song_id: str,
    payload: schemas.ScoreSubmissionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    machine = db.query(Machine).filter(Machine.id == song.machine_id).first()
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    tournament = db.query(Tournament).filter(Tournament.id == machine.tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")

    t_service = TournamentService(db=db, actor=current_user)
    t_service.ensure_actor_can_view(tournament)

    score_service = ScoreService(db=db, actor=current_user)
    submission = score_service.submit_score(
        song=song,
        tournament=tournament,
        score=payload.score,
        photo_key=payload.photo_key,
        comment=payload.comment,
    )
    return schemas.ScoreSubmissionRead.from_orm(submission)


@router.get("/my/submissions", response_model=list[schemas.ScoreSubmissionRead])
def my_submissions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = ScoreService(db=db, actor=current_user)
    submissions = service.list_my_submissions()
    return [schemas.ScoreSubmissionRead.from_orm(s) for s in submissions]


@router.get("/admin/tournaments/{tournament_id}/submissions", response_model=list[schemas.ScoreSubmissionRead])
def tournament_submissions(
    tournament_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in {Role.SUPERADMIN, Role.KBM_ADMIN, Role.BBD_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    t_service = TournamentService(db=db, actor=current_user)
    tournament = t_service.get(tournament_id)
    t_service.ensure_actor_can_manage(tournament)
    service = ScoreService(db=db, actor=current_user)
    submissions = service.list_for_tournament(tournament)
    return [schemas.ScoreSubmissionRead.from_orm(s) for s in submissions]

"""Score review endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, get_db
from ..models import Machine, ReviewStatus, Role, ScoreSubmission, Song, Tournament, User
from ..schemas.reviews import ReviewDecision
from ..schemas.submissions import ScoreSubmissionRead
from ..services.submissions import ScoreService
from ..services.tournaments import TournamentService

router = APIRouter(prefix="/api/kbd_ir", tags=["reviews"])

ADMIN_ROLES = {Role.SUPERADMIN, Role.KBM_ADMIN, Role.BBD_ADMIN}


def _manageable_tournament_ids(db: Session, current_user: User) -> set[str]:
    service = TournamentService(db=db, actor=current_user)
    tournament_ids: set[str] = set()
    for tournament in db.query(Tournament).all():
        try:
            service.ensure_actor_can_manage(tournament)
            tournament_ids.add(tournament.id)
        except HTTPException:
            continue
    return tournament_ids


@router.get("/reviews/pending", response_model=list[ScoreSubmissionRead])
def list_pending_reviews(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    allowed_tournaments = _manageable_tournament_ids(db, current_user)
    submissions_query = (
        db.query(ScoreSubmission)
        .join(Song, Song.id == ScoreSubmission.song_id)
        .join(Machine, Machine.id == Song.machine_id)
    )
    if current_user.role != Role.SUPERADMIN:
        submissions_query = submissions_query.filter(Machine.tournament_id.in_(allowed_tournaments))
    submissions = (
        submissions_query
        .filter(ScoreSubmission.review_status == ReviewStatus.PENDING)
        .order_by(ScoreSubmission.submitted_at.asc())
        .all()
    )
    return [ScoreSubmissionRead.from_orm(s) for s in submissions]


@router.post("/reviews/{submission_id}", response_model=ScoreSubmissionRead)
def review_submission(
    submission_id: str,
    payload: ReviewDecision,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    submission = (
        db.query(ScoreSubmission)
        .join(Song, Song.id == ScoreSubmission.song_id)
        .join(Machine, Machine.id == Song.machine_id)
        .filter(ScoreSubmission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    machine = db.query(Machine).filter(Machine.id == submission.song.machine_id).first()
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    tournament = db.query(Tournament).filter(Tournament.id == machine.tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")

    t_service = TournamentService(db=db, actor=current_user)
    t_service.ensure_actor_can_manage(tournament)

    score_service = ScoreService(db=db, actor=current_user)
    submission = score_service.update_review(
        submission=submission,
        reviewer=current_user,
        decision=payload.decision,
        comment=payload.comment,
    )
    return ScoreSubmissionRead.from_orm(submission)

"""Score submission service."""
from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..models import ReviewStatus, ScoreReview, ScoreSubmission, Song, Tournament, User


class ScoreService:
    def __init__(self, db: Session, actor: User) -> None:
        self.db = db
        self.actor = actor

    def submit_score(self, song: Song, tournament: Tournament, score: int, photo_key: str, comment: Optional[str]) -> ScoreSubmission:
        cap = song.score_cap_override or tournament.score_cap_default
        if score > cap:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Score exceeds cap")

        existing = (
            self.db.query(ScoreSubmission)
            .filter(ScoreSubmission.song_id == song.id, ScoreSubmission.user_id == self.actor.id)
            .first()
        )
        if existing:
            self.db.delete(existing)
            self.db.flush()

        submission = ScoreSubmission(
            id=str(uuid4()),
            song_id=song.id,
            user_id=self.actor.id,
            score=score,
            photo_key=photo_key,
            review_status=ReviewStatus.PENDING,
            review_comment=comment,
        )
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def list_my_submissions(self) -> List[ScoreSubmission]:
        return (
            self.db.query(ScoreSubmission)
            .filter(ScoreSubmission.user_id == self.actor.id)
            .order_by(ScoreSubmission.submitted_at.desc())
            .all()
        )

    def list_for_tournament(self, tournament: Tournament) -> List[ScoreSubmission]:
        song_ids = [song.id for machine in tournament.machines for song in machine.songs]
        if not song_ids:
            return []
        return (
            self.db.query(ScoreSubmission)
            .filter(ScoreSubmission.song_id.in_(song_ids))
            .order_by(ScoreSubmission.submitted_at.desc())
            .all()
        )

    def next_pending(self) -> Optional[ScoreSubmission]:
        return (
            self.db.query(ScoreSubmission)
            .filter(ScoreSubmission.review_status == ReviewStatus.PENDING)
            .order_by(ScoreSubmission.submitted_at.asc())
            .first()
        )

    def update_review(self, submission: ScoreSubmission, reviewer: User, decision: ReviewStatus, comment: Optional[str]) -> ScoreSubmission:
        if decision not in {ReviewStatus.APPROVED, ReviewStatus.REJECTED}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid decision")
        submission.review_status = decision
        submission.review_comment = comment
        review = ScoreReview(
            id=str(uuid4()),
            submission_id=submission.id,
            reviewer_user_id=reviewer.id,
            decision=decision,
            comment=comment,
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(submission)
        return submission

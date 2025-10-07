"""Tournament domain services."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import (
    Circle,
    CircleScope,
    Machine,
    Role,
    Song,
    Tournament,
    TournamentStatus,
    TournamentVisibility,
    User,
)


class TournamentService:
    def __init__(self, db: Session, actor: User) -> None:
        self.db = db
        self.actor = actor

    def list_accessible(self) -> List[Tournament]:
        query = self.db.query(Tournament)
        if self.actor.role == Role.SUPERADMIN:
            return query.order_by(Tournament.created_at.desc()).all()

        allowed_scopes = {CircleScope.JOINT}
        if self.actor.role in {Role.KBM_ADMIN, Role.KBM_USER}:
            allowed_scopes.add(CircleScope.KBM)
        if self.actor.role in {Role.BBD_ADMIN, Role.BBD_USER}:
            allowed_scopes.add(CircleScope.BBD)

        query = query.filter(Tournament.circle_scope.in_(allowed_scopes))

        if self.actor.role not in {Role.SUPERADMIN, Role.KBM_ADMIN, Role.BBD_ADMIN}:
            query = query.filter(Tournament.visibility == TournamentVisibility.PUBLIC)

        return query.order_by(Tournament.created_at.desc()).all()

    def get(self, tournament_id: str) -> Tournament:
        tournament = self.db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not tournament:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
        return tournament

    def get_by_slug(self, slug: str) -> Tournament:
        tournament = self.db.query(Tournament).filter(Tournament.slug == slug).first()
        if not tournament:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found")
        return tournament

    def ensure_actor_can_view(self, tournament: Tournament) -> None:
        if tournament.visibility == TournamentVisibility.OPS_TEST and self.actor.role not in {
            Role.SUPERADMIN,
            Role.KBM_ADMIN,
            Role.BBD_ADMIN,
        }:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        if tournament.circle_scope == CircleScope.JOINT:
            return
        if tournament.circle_scope == CircleScope.KBM and self.actor.role not in {
            Role.SUPERADMIN,
            Role.KBM_ADMIN,
            Role.KBM_USER,
        }:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        if tournament.circle_scope == CircleScope.BBD and self.actor.role not in {
            Role.SUPERADMIN,
            Role.BBD_ADMIN,
            Role.BBD_USER,
        }:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    def create_tournament(
        self,
        name: str,
        slug: str,
        circle_scope: CircleScope,
        visibility: TournamentVisibility,
        status: TournamentStatus,
        registration_opens: Optional[datetime],
        registration_closes: Optional[datetime],
        event_starts: Optional[datetime],
        event_ends: Optional[datetime],
        score_cap_default: int,
    ) -> Tournament:
        existing = self.db.query(Tournament).filter(Tournament.slug == slug).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug already exists")

        tournament = Tournament(
            id=str(uuid4()),
            name=name,
            slug=slug,
            circle_scope=circle_scope,
            visibility=visibility,
            status=status,
            registration_opens=registration_opens,
            registration_closes=registration_closes,
            event_starts=event_starts,
            event_ends=event_ends,
            score_cap_default=score_cap_default,
            created_by_user_id=self.actor.id,
        )
        self.db.add(tournament)
        self.db.commit()
        self.db.refresh(tournament)
        return tournament

    def update_tournament(self, tournament: Tournament, **kwargs) -> Tournament:
        for key, value in kwargs.items():
            if value is not None:
                setattr(tournament, key, value)
        self.db.commit()
        self.db.refresh(tournament)
        return tournament

    def create_machine(self, tournament: Tournament, name: str, game_code: str, description: Optional[str]) -> Machine:
        machine = Machine(
            id=str(uuid4()),
            tournament_id=tournament.id,
            name=name,
            game_code=game_code,
            description=description,
        )
        self.db.add(machine)
        self.db.commit()
        self.db.refresh(machine)
        return machine

    def update_machine(self, machine: Machine, **kwargs) -> Machine:
        for key, value in kwargs.items():
            if value is not None:
                setattr(machine, key, value)
        self.db.commit()
        self.db.refresh(machine)
        return machine

    def delete_machine(self, machine: Machine) -> None:
        self.db.delete(machine)
        self.db.commit()

    def create_song(
        self,
        machine: Machine,
        title: str,
        artist: Optional[str],
        difficulty: str,
        score_cap_override: Optional[int],
        optional_metadata: Optional[dict],
    ) -> Song:
        song = Song(
            id=str(uuid4()),
            machine_id=machine.id,
            title=title,
            artist=artist,
            difficulty=difficulty,
            score_cap_override=score_cap_override,
            optional_metadata=optional_metadata,
        )
        self.db.add(song)
        self.db.commit()
        self.db.refresh(song)
        return song

    def update_song(self, song: Song, **kwargs) -> Song:
        for key, value in kwargs.items():
            if value is not None:
                setattr(song, key, value)
        self.db.commit()
        self.db.refresh(song)
        return song

    def delete_song(self, song: Song) -> None:
        self.db.delete(song)
        self.db.commit()

    def ensure_actor_can_manage(self, tournament: Tournament) -> None:
        if self.actor.role == Role.SUPERADMIN:
            return
        if tournament.visibility == TournamentVisibility.OPS_TEST and self.actor.role not in {
            Role.KBM_ADMIN,
            Role.BBD_ADMIN,
        }:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        if tournament.circle_scope == CircleScope.JOINT:
            if self.actor.role in {Role.KBM_ADMIN, Role.BBD_ADMIN}:
                return
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        circle_required = Circle.KBM if tournament.circle_scope == CircleScope.KBM else Circle.BBD
        if (circle_required == Circle.KBM and self.actor.role != Role.KBM_ADMIN) or (
            circle_required == Circle.BBD and self.actor.role != Role.BBD_ADMIN
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

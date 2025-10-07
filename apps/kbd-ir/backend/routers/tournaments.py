"""Tournament and catalog endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, get_db
from ..models import Machine, Role, Song, TournamentVisibility, User
from ..schemas import tournaments as schemas
from ..services.tournaments import TournamentService

router = APIRouter(prefix="/api/kbd_ir", tags=["tournaments"])


@router.get("/tournaments", response_model=list[schemas.TournamentBase])
def list_tournaments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = TournamentService(db=db, actor=current_user)
    tournaments = service.list_accessible()
    return [schemas.TournamentBase.from_orm(t) for t in tournaments]


@router.post("/tournaments", response_model=schemas.TournamentBase)
def create_tournament(
    payload: schemas.TournamentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in {Role.SUPERADMIN, Role.KBM_ADMIN, Role.BBD_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    service = TournamentService(db=db, actor=current_user)
    tournament = service.create_tournament(
        name=payload.name,
        slug=payload.slug,
        circle_scope=payload.circle_scope,
        visibility=payload.visibility,
        status=payload.status,
        registration_opens=payload.registration_opens,
        registration_closes=payload.registration_closes,
        event_starts=payload.event_starts,
        event_ends=payload.event_ends,
        score_cap_default=payload.score_cap_default,
    )
    return schemas.TournamentBase.from_orm(tournament)


@router.get("/tournaments/{tournament_id}", response_model=schemas.TournamentDetail)
def get_tournament(
    tournament_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TournamentService(db=db, actor=current_user)
    tournament = service.get(tournament_id)
    service.ensure_actor_can_view(tournament)
    return schemas.TournamentDetail.from_orm(tournament)


@router.patch("/tournaments/{tournament_id}", response_model=schemas.TournamentBase)
def update_tournament(
    tournament_id: str,
    payload: schemas.TournamentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TournamentService(db=db, actor=current_user)
    tournament = service.get(tournament_id)
    service.ensure_actor_can_manage(tournament)
    tournament = service.update_tournament(tournament, **payload.dict(exclude_unset=True))
    return schemas.TournamentBase.from_orm(tournament)


@router.post("/tournaments/{tournament_id}/machines", response_model=schemas.MachineDetail)
def add_machine(
    tournament_id: str,
    payload: schemas.MachineCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TournamentService(db=db, actor=current_user)
    tournament = service.get(tournament_id)
    service.ensure_actor_can_manage(tournament)
    machine = service.create_machine(
        tournament=tournament,
        name=payload.name,
        game_code=payload.game_code,
        description=payload.description,
    )
    return schemas.MachineDetail.from_orm(machine)


@router.patch("/machines/{machine_id}", response_model=schemas.MachineDetail)
def update_machine(
    machine_id: str,
    payload: schemas.MachineUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TournamentService(db=db, actor=current_user)
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    tournament = service.get(machine.tournament_id)
    service.ensure_actor_can_manage(tournament)
    machine = service.update_machine(machine, **payload.dict(exclude_unset=True))
    return schemas.MachineDetail.from_orm(machine)


@router.delete("/machines/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_machine(
    machine_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TournamentService(db=db, actor=current_user)
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    tournament = service.get(machine.tournament_id)
    service.ensure_actor_can_manage(tournament)
    service.delete_machine(machine)
    return None


@router.post("/machines/{machine_id}/songs", response_model=schemas.SongBase)
def add_song(
    machine_id: str,
    payload: schemas.SongCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TournamentService(db=db, actor=current_user)
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    tournament = service.get(machine.tournament_id)
    service.ensure_actor_can_manage(tournament)
    song = service.create_song(
        machine=machine,
        title=payload.title,
        artist=payload.artist,
        difficulty=payload.difficulty,
        score_cap_override=payload.score_cap_override,
        optional_metadata=payload.optional_metadata,
    )
    return schemas.SongBase.from_orm(song)


@router.patch("/songs/{song_id}", response_model=schemas.SongBase)
def update_song(
    song_id: str,
    payload: schemas.SongUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TournamentService(db=db, actor=current_user)
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    machine = db.query(Machine).filter(Machine.id == song.machine_id).first()
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    tournament = service.get(machine.tournament_id)
    service.ensure_actor_can_manage(tournament)
    song = service.update_song(song, **payload.dict(exclude_unset=True))
    return schemas.SongBase.from_orm(song)


@router.delete("/songs/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_song(
    song_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TournamentService(db=db, actor=current_user)
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    machine = db.query(Machine).filter(Machine.id == song.machine_id).first()
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    tournament = service.get(machine.tournament_id)
    service.ensure_actor_can_manage(tournament)
    service.delete_song(song)
    return None

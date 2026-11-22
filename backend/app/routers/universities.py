from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import University, User, UserRole
from app.repositories.universities import list_visible_universities, visible_university
from app.schemas.api import UniversityRead, UniversityRegistrationOption, UniversityUpdate

router = APIRouter(prefix="/universities", tags=["Universidades"])


@router.get("/registration-options", response_model=list[UniversityRegistrationOption])
def registration_options(db: Session = Depends(get_db)) -> list[University]:
    query = (
        select(University)
        .where(University.active.is_(True), University.public_registration_enabled.is_(True))
        .order_by(University.name)
    )
    return list(db.scalars(query).all())


@router.get("", response_model=list[UniversityRead])
def list_universities(
    active: bool | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_visible_universities(db, user, active=active)


@router.get("/{university_id}", response_model=UniversityRead)
def get_university(
    university_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    university = visible_university(db, university_id, user)
    if university is None:
        raise HTTPException(status_code=404, detail="Universidad no encontrada")
    return university


@router.patch("/{university_id}", response_model=UniversityRead)
def update_university(
    university_id: UUID,
    payload: UniversityUpdate,
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    university = db.get(University, university_id)
    if university is None:
        raise HTTPException(status_code=404, detail="Universidad no encontrada")
    changes = payload.model_dump(exclude_unset=True)
    if not changes or any(value is None for key, value in changes.items() if key != "address"):
        raise HTTPException(status_code=422, detail="No hay datos válidos para actualizar")
    for field, value in changes.items():
        setattr(university, field, value)
    try:
        db.commit()
        db.refresh(university)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El identificador de universidad ya está registrado") from exc
    return university

from uuid import UUID

from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import User, UserRole
from app.repositories.operations import citizen_deposits, visible_deposit, visible_deposits
from app.schemas.api import DepositCreate, DepositRead
from app.services.deposits import register_deposit

router = APIRouter(prefix="/deposits", tags=["Depósitos"])
citizen_only = require_roles(UserRole.CITIZEN)
deposit_reader = require_roles(UserRole.ADMIN, UserRole.CITIZEN)


@router.post("", response_model=DepositRead, status_code=status.HTTP_201_CREATED)
def create_deposit(payload: DepositCreate, user: User = Depends(citizen_only), db: Session = Depends(get_db)):
    return register_deposit(db, user, payload)


@router.get("/me", response_model=list[DepositRead])
def my_deposits(user: User = Depends(citizen_only), db: Session = Depends(get_db)):
    return citizen_deposits(db, user)


@router.get("", response_model=list[DepositRead])
def list_deposits(
    university_id: UUID | None = None,
    user_id: UUID | None = None,
    material_id: UUID | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(deposit_reader),
    db: Session = Depends(get_db),
):
    if user.role == UserRole.CITIZEN:
        if user_id not in (None, user.id):
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if university_id not in (None, user.university_id):
            raise HTTPException(status_code=404, detail="Universidad no encontrada")
    if from_date is not None:
        from_date = from_date.replace(tzinfo=UTC) if from_date.tzinfo is None else from_date.astimezone(UTC)
    if to_date is not None:
        to_date = to_date.replace(tzinfo=UTC) if to_date.tzinfo is None else to_date.astimezone(UTC)
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="El rango de fechas no es válido")
    return visible_deposits(
        db, user, university_id=university_id, user_id=user_id,
        material_id=material_id, from_date=from_date, to_date=to_date,
        offset=offset, limit=limit,
    )


@router.get("/{deposit_id}", response_model=DepositRead)
def get_deposit(deposit_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deposit = visible_deposit(db, deposit_id, user)
    if deposit is None:
        raise HTTPException(status_code=404, detail="Depósito no encontrado")
    return deposit

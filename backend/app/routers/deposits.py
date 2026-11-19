from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import Deposit, User, UserRole
from app.repositories.operations import citizen_deposits, get_or_404
from app.schemas.api import DepositCreate, DepositRead
from app.services.deposits import register_deposit

router = APIRouter(prefix="/deposits", tags=["Depósitos"])
citizen_only = require_roles(UserRole.CITIZEN)


@router.post("", response_model=DepositRead, status_code=status.HTTP_201_CREATED)
def create_deposit(payload: DepositCreate, user: User = Depends(citizen_only), db: Session = Depends(get_db)):
    return register_deposit(db, user, payload)


@router.get("/me", response_model=list[DepositRead])
def my_deposits(user: User = Depends(citizen_only), db: Session = Depends(get_db)):
    return citizen_deposits(db, user)


@router.get("/{deposit_id}", response_model=DepositRead)
def get_deposit(deposit_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deposit = get_or_404(db, Deposit, deposit_id, "Depósito")
    if user.role != UserRole.ADMIN and deposit.citizen_id != user.id:
        raise HTTPException(status_code=404, detail="Depósito no encontrado")
    return deposit

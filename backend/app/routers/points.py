from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import require_roles
from app.models import PointTransaction, TransactionType, User, UserRole
from app.repositories.operations import user_transactions
from app.schemas.api import BalanceRead, PointTransactionRead

router = APIRouter(prefix="/points", tags=["EcoPuntos"])
citizen_only = require_roles(UserRole.CITIZEN)


@router.get("/balance", response_model=BalanceRead)
def balance(user: User = Depends(citizen_only), db: Session = Depends(get_db)):
    amount = db.scalar(select(func.coalesce(func.sum(PointTransaction.amount), 0)).where(PointTransaction.user_id == user.id))
    return BalanceRead(balance=Decimal(amount))


@router.get("/transactions", response_model=list[PointTransactionRead])
def transactions(user: User = Depends(citizen_only), db: Session = Depends(get_db)):
    return user_transactions(db, user)

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Collection, Deposit, EcoPoint, Material, PointTransaction, User


def get_or_404(db: Session, model: type, item_id: UUID, label: str):
    item = db.get(model, item_id)
    if item is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"{label} no encontrado")
    return item


def list_alerts(db: Session):
    return db.scalars(select(Alert).order_by(Alert.created_at.desc())).all()


def citizen_deposits(db: Session, user: User):
    return db.scalars(select(Deposit).where(Deposit.citizen_id == user.id).order_by(Deposit.created_at.desc())).all()


def visible_collections(db: Session, user: User):
    query = select(Collection).order_by(Collection.created_at.desc())
    if user.role.value == "RECYCLER":
        query = query.where(Collection.recycler_id == user.id)
    return db.scalars(query).all()


def list_materials(db: Session):
    return db.scalars(select(Material).order_by(Material.name)).all()


def list_ecopoints(db: Session):
    return db.scalars(select(EcoPoint).order_by(EcoPoint.name)).all()


def user_transactions(db: Session, user: User):
    return db.scalars(select(PointTransaction).where(PointTransaction.user_id == user.id).order_by(PointTransaction.created_at.desc())).all()

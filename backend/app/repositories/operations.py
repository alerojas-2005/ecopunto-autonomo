from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Alert, Collection, Compartment, Deposit, EcoPoint, Material, PointTransaction,
    User, UserRole,
)


def get_or_404(db: Session, model: type, item_id: UUID, label: str):
    item = db.get(model, item_id)
    if item is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"{label} no encontrado")
    return item


def list_alerts(db: Session, user: User):
    if user.role not in (UserRole.ADMIN, UserRole.RECYCLER):
        return []
    query = select(Alert).join(Alert.compartment).join(Compartment.ecopoint)
    if user.role != UserRole.ADMIN:
        query = query.where(EcoPoint.university_id == user.university_id)
    return db.scalars(query.order_by(Alert.created_at.desc())).all()


def visible_alert(db: Session, alert_id: UUID, user: User) -> Alert | None:
    if user.role not in (UserRole.ADMIN, UserRole.RECYCLER):
        return None
    query = select(Alert).join(Alert.compartment).join(Compartment.ecopoint).where(Alert.id == alert_id)
    if user.role != UserRole.ADMIN:
        query = query.where(EcoPoint.university_id == user.university_id)
    return db.scalar(query)


def citizen_deposits(db: Session, user: User):
    return db.scalars(select(Deposit).where(Deposit.citizen_id == user.id).order_by(Deposit.created_at.desc())).all()


def visible_collections(db: Session, user: User):
    if user.role not in (UserRole.ADMIN, UserRole.RECYCLER):
        return []
    query = select(Collection).join(Collection.ecopoint)
    if user.role == UserRole.RECYCLER:
        query = query.where(
            Collection.recycler_id == user.id,
            EcoPoint.university_id == user.university_id,
        )
    return db.scalars(query.order_by(Collection.created_at.desc())).all()


def visible_collection(db: Session, collection_id: UUID, user: User) -> Collection | None:
    if user.role not in (UserRole.ADMIN, UserRole.RECYCLER):
        return None
    query = select(Collection).join(Collection.ecopoint).where(Collection.id == collection_id)
    if user.role == UserRole.RECYCLER:
        query = query.where(
            Collection.recycler_id == user.id,
            EcoPoint.university_id == user.university_id,
        )
    elif user.role != UserRole.ADMIN:
        return None
    return db.scalar(query)


def visible_deposit(db: Session, deposit_id: UUID, user: User) -> Deposit | None:
    query = select(Deposit).where(Deposit.id == deposit_id)
    if user.role == UserRole.CITIZEN:
        query = query.where(Deposit.citizen_id == user.id)
    elif user.role != UserRole.ADMIN:
        return None
    return db.scalar(query)


def visible_deposits(
    db: Session,
    user: User,
    *,
    university_id: UUID | None = None,
    user_id: UUID | None = None,
    material_id: UUID | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[Deposit]:
    query = select(Deposit).join(Deposit.ecopoint)
    if user.role == UserRole.ADMIN:
        if university_id is not None:
            query = query.where(EcoPoint.university_id == university_id)
    elif user.role == UserRole.CITIZEN:
        query = query.where(Deposit.citizen_id == user.id)
        if user.university_id is not None:
            query = query.where(EcoPoint.university_id == user.university_id)
        if user_id is not None:
            query = query.where(Deposit.citizen_id == user_id)
    else:
        return []
    if user_id is not None and user.role != UserRole.CITIZEN:
        query = query.where(Deposit.citizen_id == user_id)
    if material_id is not None:
        query = query.where(Deposit.material_id == material_id)
    if from_date is not None:
        query = query.where(Deposit.created_at >= from_date)
    if to_date is not None:
        query = query.where(Deposit.created_at <= to_date)
    return db.scalars(
        query.order_by(Deposit.created_at.desc()).offset(offset).limit(limit)
    ).all()


def visible_ecopoints(db: Session, user: User):
    query = select(EcoPoint)
    if user.role != UserRole.ADMIN:
        query = query.where(EcoPoint.university_id == user.university_id)
    if user.role != UserRole.ADMIN:
        query = query.where(EcoPoint.active.is_(True))
    return db.scalars(query.order_by(EcoPoint.name)).all()


def visible_ecopoint(db: Session, ecopoint_id: UUID, user: User) -> EcoPoint | None:
    query = select(EcoPoint).where(EcoPoint.id == ecopoint_id)
    if user.role != UserRole.ADMIN:
        query = query.where(EcoPoint.university_id == user.university_id)
    if user.role != UserRole.ADMIN:
        query = query.where(EcoPoint.active.is_(True))
    return db.scalar(query)


def visible_compartment(db: Session, compartment_id: UUID, user: User) -> Compartment | None:
    query = select(Compartment).join(Compartment.ecopoint).where(Compartment.id == compartment_id)
    if user.role != UserRole.ADMIN:
        query = query.where(EcoPoint.university_id == user.university_id)
    if user.role != UserRole.ADMIN:
        query = query.where(EcoPoint.active.is_(True), Compartment.active.is_(True))
    return db.scalar(query)


def list_materials(db: Session):
    return db.scalars(select(Material).order_by(Material.name)).all()


def user_transactions(db: Session, user: User):
    return db.scalars(select(PointTransaction).where(PointTransaction.user_id == user.id).order_by(PointTransaction.created_at.desc())).all()

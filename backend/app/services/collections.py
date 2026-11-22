from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, AlertStatus, Collection, Compartment, EcoPoint, User
from app.schemas.api import CollectionCreate


def register_collection(db: Session, recycler: User, payload: CollectionCreate) -> Collection:
    if recycler.university_id is None:
        raise HTTPException(status_code=403, detail="El reciclador no tiene universidad asignada")
    ecopoint = db.scalar(select(EcoPoint).where(
        EcoPoint.id == payload.ecopoint_id,
        EcoPoint.university_id == recycler.university_id,
    ))
    if ecopoint is None:
        raise HTTPException(status_code=404, detail="EcoPunto no encontrado")
    compartment = db.scalar(select(Compartment).where(
        Compartment.id == payload.compartment_id,
        Compartment.ecopoint_id == ecopoint.id,
    ))
    if compartment is None:
        raise HTTPException(status_code=404, detail="Compartimento no encontrado")
    amount = Decimal(payload.weight_kg)
    if amount > Decimal(compartment.current_kg):
        raise HTTPException(status_code=409, detail="El peso recolectado supera el peso registrado en el compartimento")
    try:
        collection = Collection(
            id=uuid4(), ecopoint_id=ecopoint.id, compartment_id=compartment.id,
            recycler_id=recycler.id, weight_kg=amount, notes=payload.notes,
        )
        db.add(collection)
        compartment.current_kg = Decimal(compartment.current_kg) - amount
        db.flush()
        if compartment.fill_percentage < Decimal(compartment.fill_threshold_pct):
            active_alerts = db.scalars(select(Alert).where(
                Alert.compartment_id == compartment.id,
                Alert.status == AlertStatus.ACTIVE,
            )).all()
            for alert in active_alerts:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(UTC)
        db.commit()
        db.refresh(collection)
        return collection
    except Exception:
        db.rollback()
        raise

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, AlertStatus, Collection, Compartment, EcoPoint, User
from app.schemas.api import CollectionCreate


def register_collection(db: Session, recycler: User, payload: CollectionCreate) -> Collection:
    ecopoint = db.get(EcoPoint, payload.ecopoint_id)
    compartment = db.get(Compartment, payload.compartment_id)
    if ecopoint is None or compartment is None:
        raise HTTPException(status_code=404, detail="EcoPunto o compartimento no encontrado")
    if compartment.ecopoint_id != ecopoint.id:
        raise HTTPException(status_code=400, detail="El compartimento no pertenece al EcoPunto indicado")
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

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (Alert, AlertStatus, AssignmentStatus, Collection, Compartment,
                        EcoPoint, RecyclerAssignment, RecyclerLinkType, RecyclerProfile, RecyclerProfileStatus,
                        User, UserRole)
from app.schemas.api import CollectionCreate


def register_collection(db: Session, recycler: User, payload: CollectionCreate) -> Collection:
    now = datetime.now(UTC)
    profile = db.get(RecyclerProfile, recycler.id)
    if profile is not None and profile.status != RecyclerProfileStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="El perfil del reciclador está suspendido o pendiente")
    point_university = select(EcoPoint.university_id).where(EcoPoint.id == payload.ecopoint_id).scalar_subquery()
    assigned = db.scalar(select(RecyclerAssignment.id).where(
        RecyclerAssignment.recycler_id == recycler.id,
        ((RecyclerAssignment.ecopoint_id == payload.ecopoint_id) | ((RecyclerAssignment.ecopoint_id.is_(None)) & (RecyclerAssignment.university_id == point_university))),
        RecyclerAssignment.status == AssignmentStatus.ACTIVE,
        RecyclerAssignment.starts_at <= now,
        (RecyclerAssignment.ends_at.is_(None) | (RecyclerAssignment.ends_at >= now)),
    ))
    has_assignments = db.scalar(select(RecyclerAssignment.id).where(RecyclerAssignment.recycler_id == recycler.id).limit(1))
    ecopoint_query = select(EcoPoint).where(EcoPoint.id == payload.ecopoint_id)
    if has_assignments:
        if not assigned:
            raise HTTPException(status_code=403, detail="No tienes una asignación activa para este EcoPunto")
    elif recycler.university_id is None:
        raise HTTPException(status_code=403, detail="El reciclador no tiene una asignación activa")
    elif profile is not None and (profile.link_type == RecyclerLinkType.ORGANIZATION or profile.organization_id is not None):
        raise HTTPException(status_code=403, detail="La organización aún no ha autorizado este EcoPunto")
    else:
        # Compatibilidad temporal con recicladores existentes antes de la migración explícita.
        ecopoint_query = ecopoint_query.where(EcoPoint.university_id == recycler.university_id)
    ecopoint = db.scalar(ecopoint_query)
    if ecopoint is None:
        raise HTTPException(status_code=404, detail="EcoPunto no encontrado")
    if not ecopoint.active:
        raise HTTPException(status_code=409, detail="El EcoPunto está inactivo")
    compartment = db.scalar(select(Compartment).where(
        Compartment.id == payload.compartment_id,
        Compartment.ecopoint_id == ecopoint.id,
    ))
    if compartment is None:
        raise HTTPException(status_code=404, detail="Compartimento no encontrado")
    if not compartment.active:
        raise HTTPException(status_code=409, detail="El compartimento está inactivo")
    amount = Decimal(payload.weight_kg)
    if amount > Decimal(compartment.current_kg):
        raise HTTPException(status_code=409, detail="El peso recolectado supera el peso registrado en el compartimento")
    try:
        collection = Collection(
            id=uuid4(), ecopoint_id=ecopoint.id, compartment_id=compartment.id,
            recycler_id=recycler.id, material_id=compartment.material_id,
            weight_kg=amount, notes=payload.notes,
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

from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    AlertStatus,
    AlertType,
    Compartment,
    Deposit,
    EcoPoint,
    Material,
    PointTransaction,
    TransactionType,
    User,
)
from app.schemas.api import DepositCreate


def award_points(weight_g: int, factor: Decimal) -> Decimal:
    """Round point values to four decimal places; exact halves round up."""
    return (Decimal(weight_g) * factor).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def register_deposit(db: Session, citizen: User, payload: DepositCreate) -> Deposit:
    if citizen.university_id is None:
        raise HTTPException(status_code=404, detail="EcoPunto no encontrado")
    ecopoint = db.scalar(select(EcoPoint).where(
        EcoPoint.id == payload.ecopoint_id,
        EcoPoint.university_id == citizen.university_id,
    ))
    if ecopoint is None:
        raise HTTPException(status_code=404, detail="EcoPunto no encontrado")
    if not ecopoint.active:
        raise HTTPException(status_code=409, detail="No se permiten depósitos en un EcoPunto inactivo")
    compartment = db.scalar(select(Compartment).where(
        Compartment.id == payload.compartment_id,
        Compartment.ecopoint_id == ecopoint.id,
    ))
    if compartment is None:
        raise HTTPException(status_code=404, detail="Compartimento no encontrado")
    if not compartment.active:
        raise HTTPException(status_code=409, detail="El compartimento esta inactivo")
    if compartment.material_id is None:
        if compartment.label != "No identificados":
            raise HTTPException(status_code=409, detail="Compartimento sin material no válido")
        if payload.material_id is not None:
            raise HTTPException(status_code=400, detail="El compartimento No identificados no admite material asignado")
        material = None
    else:
        if payload.material_id != compartment.material_id:
            raise HTTPException(status_code=400, detail="El compartimento no corresponde al material indicado")
        material = db.get(Material, compartment.material_id)
        if material is None:
            raise HTTPException(status_code=404, detail="Material no encontrado")
        if not material.active:
            raise HTTPException(status_code=409, detail="El material esta inactivo")

    added_kg = Decimal(payload.weight_g) / Decimal("1000")
    new_weight = Decimal(compartment.current_kg) + added_kg
    if new_weight > Decimal(compartment.capacity_kg):
        raise HTTPException(status_code=409, detail="El depósito supera la capacidad disponible del compartimento")
    factor = Decimal(material.points_per_gram) if material is not None else Decimal("0")
    points = award_points(payload.weight_g, factor) if material is not None else Decimal("0")

    try:
        deposit = Deposit(
            id=uuid4(), citizen_id=citizen.id, ecopoint_id=ecopoint.id,
            compartment_id=compartment.id, material_id=material.id if material is not None else None,
            weight_g=payload.weight_g, factor_applied=factor,
            points_awarded=points,
        )
        db.add(deposit)
        compartment.current_kg = new_weight
        db.flush()
        if material is not None:
            db.add(PointTransaction(
                id=uuid4(), user_id=citizen.id, deposit_id=deposit.id,
                type=TransactionType.EARN, amount=points,
                description=f"Depósito de {material.name} ({payload.weight_g} g)",
            ))
        if compartment.fill_percentage >= Decimal(compartment.fill_threshold_pct):
            active_alert = db.scalar(select(Alert).where(
                Alert.compartment_id == compartment.id,
                Alert.type == AlertType.FILL_THRESHOLD,
                Alert.status == AlertStatus.ACTIVE,
            ))
            if active_alert is None:
                db.add(Alert(
                    id=uuid4(), compartment_id=compartment.id,
                    type=AlertType.FILL_THRESHOLD, status=AlertStatus.ACTIVE,
                    message=f"{ecopoint.name} · {compartment.label} alcanzó {compartment.fill_percentage}% de llenado",
                ))
        db.commit()
        db.refresh(deposit)
        return deposit
    except Exception:
        db.rollback()
        raise

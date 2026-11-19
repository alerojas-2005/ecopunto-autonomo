from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import Compartment, EcoPoint, Material, User, UserRole
from app.repositories.operations import get_or_404, list_ecopoints, list_materials
from app.schemas.api import (
    CompartmentCreate,
    CompartmentRead,
    CompartmentPatch,
    EcoPointCreate,
    EcoPointPatch,
    EcoPointRead,
    MaterialCreate,
    MaterialPatch,
    MaterialRead,
)

router = APIRouter(tags=["Catálogo y EcoPuntos"])
admin_only = require_roles(UserRole.ADMIN)


def save(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El código o nombre ya está registrado") from exc


@router.get("/materials", response_model=list[MaterialRead])
def get_materials(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    materials = list_materials(db)
    return materials if user.role == UserRole.ADMIN else [material for material in materials if material.active]


@router.post("/materials", response_model=MaterialRead, status_code=status.HTTP_201_CREATED)
def create_material(payload: MaterialCreate, _admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    material = Material(**payload.model_dump())
    db.add(material)
    save(db)
    db.refresh(material)
    return material


@router.patch("/materials/{material_id}", response_model=MaterialRead)
def patch_material(material_id: UUID, payload: MaterialPatch, _admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    material = get_or_404(db, Material, material_id, "Material")
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for key, value in changes.items() if key != "description"):
        raise HTTPException(status_code=422, detail="Los campos modificables no pueden ser null")
    for key, value in changes.items():
        setattr(material, key, value)
    save(db)
    db.refresh(material)
    return material


@router.get("/ecopoints", response_model=list[EcoPointRead])
def get_ecopoints(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = list_ecopoints(db)
    return items if user.role == UserRole.ADMIN else [item for item in items if item.active]


@router.get("/ecopoints/{ecopoint_id}", response_model=EcoPointRead)
def get_ecopoint(ecopoint_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = get_or_404(db, EcoPoint, ecopoint_id, "EcoPunto")
    if not item.active and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="EcoPunto no encontrado")
    return item


@router.post("/ecopoints", response_model=EcoPointRead, status_code=status.HTTP_201_CREATED)
def create_ecopoint(payload: EcoPointCreate, _admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    item = EcoPoint(**payload.model_dump())
    db.add(item)
    save(db)
    db.refresh(item)
    return item


@router.patch("/ecopoints/{ecopoint_id}", response_model=EcoPointRead)
def patch_ecopoint(ecopoint_id: UUID, payload: EcoPointPatch, _admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    item = get_or_404(db, EcoPoint, ecopoint_id, "EcoPunto")
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail="Los campos modificables no pueden ser null")
    for key, value in changes.items():
        setattr(item, key, value)
    save(db)
    db.refresh(item)
    return item


@router.get("/ecopoints/{ecopoint_id}/compartments", response_model=list[CompartmentRead])
def get_compartments(ecopoint_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ecopoint = get_or_404(db, EcoPoint, ecopoint_id, "EcoPunto")
    if not ecopoint.active and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=404, detail="EcoPunto no encontrado")
    query = select(Compartment).where(Compartment.ecopoint_id == ecopoint_id).order_by(Compartment.label)
    compartments = db.scalars(query).all()
    return compartments if user.role == UserRole.ADMIN else [compartment for compartment in compartments if compartment.active]


@router.post("/ecopoints/{ecopoint_id}/compartments", response_model=CompartmentRead, status_code=status.HTTP_201_CREATED)
def create_compartment(ecopoint_id: UUID, payload: CompartmentCreate, _admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    ecopoint = get_or_404(db, EcoPoint, ecopoint_id, "EcoPunto")
    material = get_or_404(db, Material, payload.material_id, "Material")
    if not material.active:
        raise HTTPException(status_code=409, detail="No se puede agregar un material inactivo")
    if payload.current_kg > payload.capacity_kg:
        raise HTTPException(status_code=422, detail="El peso actual no puede superar la capacidad")
    compartment = Compartment(ecopoint_id=ecopoint.id, **payload.model_dump())
    db.add(compartment)
    save(db)
    db.refresh(compartment)
    return compartment


@router.patch("/compartments/{compartment_id}", response_model=CompartmentRead)
def patch_compartment(compartment_id: UUID, payload: CompartmentPatch, _admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    compartment = get_or_404(db, Compartment, compartment_id, "Compartimento")
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail="Los campos modificables no pueden ser null")
    if "capacity_kg" in changes and changes["capacity_kg"] < compartment.current_kg:
        raise HTTPException(status_code=422, detail="La capacidad no puede ser menor al peso actual")
    for key, value in changes.items():
        setattr(compartment, key, value)
    save(db)
    db.refresh(compartment)
    return compartment

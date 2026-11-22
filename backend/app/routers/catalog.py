from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import Compartment, EcoPoint, Material, University, User, UserRole
from app.repositories.operations import (
    get_or_404, list_materials, visible_compartment, visible_ecopoint, visible_ecopoints,
)
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
ecopoint_manager = admin_only


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
    return visible_ecopoints(db, user)


@router.get("/ecopoints/{ecopoint_id}", response_model=EcoPointRead)
def get_ecopoint(ecopoint_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = visible_ecopoint(db, ecopoint_id, user)
    if item is None:
        raise HTTPException(status_code=404, detail="EcoPunto no encontrado")
    return item


@router.post("/ecopoints", response_model=EcoPointRead, status_code=status.HTTP_201_CREATED)
def create_ecopoint(payload: EcoPointCreate, user: User = Depends(ecopoint_manager), db: Session = Depends(get_db)):
    if payload.university_id is None:
        raise HTTPException(status_code=422, detail="La universidad es obligatoria")
    university_id = payload.university_id
    if db.get(University, university_id) is None:
        raise HTTPException(status_code=404, detail="Universidad no encontrada")
    item = EcoPoint(university_id=university_id, **payload.model_dump(exclude={"university_id"}))
    db.add(item)
    save(db)
    db.refresh(item)
    return item


@router.patch("/ecopoints/{ecopoint_id}", response_model=EcoPointRead)
def patch_ecopoint(ecopoint_id: UUID, payload: EcoPointPatch, user: User = Depends(ecopoint_manager), db: Session = Depends(get_db)):
    item = visible_ecopoint(db, ecopoint_id, user)
    if item is None:
        raise HTTPException(status_code=404, detail="EcoPunto no encontrado")
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
    ecopoint = visible_ecopoint(db, ecopoint_id, user)
    if ecopoint is None:
        raise HTTPException(status_code=404, detail="EcoPunto no encontrado")
    query = select(Compartment).where(Compartment.ecopoint_id == ecopoint_id).order_by(Compartment.label)
    compartments = db.scalars(query).all()
    return compartments if user.role == UserRole.ADMIN else [compartment for compartment in compartments if compartment.active]


@router.post("/ecopoints/{ecopoint_id}/compartments", response_model=CompartmentRead, status_code=status.HTTP_201_CREATED)
def create_compartment(ecopoint_id: UUID, payload: CompartmentCreate, user: User = Depends(ecopoint_manager), db: Session = Depends(get_db)):
    ecopoint = visible_ecopoint(db, ecopoint_id, user)
    if ecopoint is None:
        raise HTTPException(status_code=404, detail="EcoPunto no encontrado")
    if payload.material_id is None and payload.label != "No identificados":
        raise HTTPException(status_code=422, detail="Los compartimentos sin material deben llamarse No identificados")
    material = db.get(Material, payload.material_id) if payload.material_id is not None else None
    if payload.material_id is not None and material is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    if material is not None and not material.active:
        raise HTTPException(status_code=409, detail="No se puede agregar un material inactivo")
    if payload.current_kg > payload.capacity_kg:
        raise HTTPException(status_code=422, detail="El peso actual no puede superar la capacidad")
    compartment = Compartment(ecopoint_id=ecopoint.id, **payload.model_dump())
    db.add(compartment)
    save(db)
    db.refresh(compartment)
    return compartment


@router.patch("/compartments/{compartment_id}", response_model=CompartmentRead)
def patch_compartment(compartment_id: UUID, payload: CompartmentPatch, user: User = Depends(ecopoint_manager), db: Session = Depends(get_db)):
    compartment = visible_compartment(db, compartment_id, user)
    if compartment is None:
        raise HTTPException(status_code=404, detail="Compartimento no encontrado")
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

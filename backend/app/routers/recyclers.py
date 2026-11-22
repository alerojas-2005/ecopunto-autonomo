from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.dependencies import get_current_user, require_roles
from app.models import (
    AssignmentStatus, Collection, Compartment, CoverageSector, EcoPoint, Organization,
    Material, OrganizationStatus, RecyclerAssignment, RecyclerLinkType, RecyclerProfile,
    RecyclerProfileStatus, University, User, UserRole,
)
from app.repositories.users import by_email
from app.schemas.api import (
    AssignmentCreate, AssignmentPatch, AssignmentRead, OrganizationCoverageUpdate,
    OrganizationCreate, OrganizationPatch, OrganizationRead, RecyclerCreate,
    RecyclerDashboardRead, RecyclerPatch, RecyclerRead, SectorCreate, SectorPatch,
    SectorPointsUpdate, SectorRead,
)
from app.services.recycler_assignments import refresh_organization_assignments, replace_recycler_organization

router = APIRouter(prefix="/recyclers", tags=["Recicladores y organizaciones"])
admin = require_roles(UserRole.ADMIN)
recycler = require_roles(UserRole.RECYCLER)


def _org_read(db: Session, item: Organization) -> OrganizationRead:
    sectors = list(item.sectors)
    point_ids = sorted({point.id for sector in sectors for point in sector.ecopoints}, key=str)
    return OrganizationRead.model_validate(item).model_copy(update={
        "sector_ids": [sector.id for sector in sectors], "ecopoint_ids": point_ids,
    })


def _sector_read(item: CoverageSector) -> SectorRead:
    return SectorRead.model_validate(item).model_copy(update={"ecopoint_ids": [point.id for point in item.ecopoints]})


def _recycler_read(db: Session, user: User) -> RecyclerRead:
    profile = db.get(RecyclerProfile, user.id)
    organization = db.get(Organization, profile.organization_id) if profile and profile.organization_id else None
    return RecyclerRead.model_validate(user).model_copy(update={
        "organization_id": profile.organization_id if profile else None,
        "organization_name": organization.name if organization else None,
        "link_type": profile.link_type if profile else RecyclerLinkType.INDEPENDENT,
        "profile_status": profile.status if profile else RecyclerProfileStatus.PENDING,
        "phone": profile.phone if profile else None,
        "document_type": profile.document_type if profile else None,
        "document_number": profile.document_number if profile else None,
    })


@router.get("/organizations", response_model=list[OrganizationRead])
def organizations(
    type: str | None = None, state: OrganizationStatus | None = None,
    q: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db), _actor: User = Depends(admin),
):
    query = select(Organization)
    if type: query = query.where(Organization.type == type)
    if state: query = query.where(Organization.status == state)
    if q: query = query.where(or_(Organization.name.ilike(f"%{q.strip()}%"), Organization.city.ilike(f"%{q.strip()}%"), Organization.tax_id.ilike(f"%{q.strip()}%")))
    return [_org_read(db, item) for item in db.scalars(query.order_by(Organization.name)).all()]


@router.post("/organizations", response_model=OrganizationRead, status_code=201)
def create_organization(payload: OrganizationCreate, db: Session = Depends(get_db), _actor: User = Depends(admin)):
    item = Organization(**payload.model_dump())
    db.add(item)
    try: db.commit()
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(409, "El NIT ya está registrado") from exc
    db.refresh(item); return _org_read(db, item)


@router.patch("/organizations/{organization_id}", response_model=OrganizationRead)
def update_organization(organization_id: UUID, payload: OrganizationPatch, db: Session = Depends(get_db), _actor: User = Depends(admin)):
    item = db.get(Organization, organization_id)
    if item is None: raise HTTPException(404, "Organización no encontrada")
    changes = payload.model_dump(exclude_unset=True)
    if any(changes.get(field) is None for field in ("name", "type", "city", "status") if field in changes):
        raise HTTPException(422, "Nombre, tipo, ciudad y estado no pueden ser null")
    for key, value in changes.items(): setattr(item, key, value)
    if "status" in changes: refresh_organization_assignments(db, item)
    try: db.commit()
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(409, "El NIT ya está registrado") from exc
    db.refresh(item); return _org_read(db, item)


@router.delete("/organizations/{organization_id}", status_code=204)
def delete_organization(organization_id: UUID, db: Session = Depends(get_db), _actor: User = Depends(admin)):
    item = db.get(Organization, organization_id)
    if item is None: raise HTTPException(404, "Organización no encontrada")
    if db.scalar(select(RecyclerProfile.user_id).where(RecyclerProfile.organization_id == item.id).limit(1)) or db.scalar(select(RecyclerAssignment.id).where(RecyclerAssignment.organization_id == item.id).limit(1)):
        raise HTTPException(409, "La organización tiene perfiles o historial; suspéndela para conservar su trazabilidad")
    db.delete(item); db.commit(); return None


@router.put("/organizations/{organization_id}/coverage", response_model=OrganizationRead)
def set_organization_coverage(organization_id: UUID, payload: OrganizationCoverageUpdate, db: Session = Depends(get_db), _actor: User = Depends(admin)):
    item = db.get(Organization, organization_id)
    if item is None: raise HTTPException(404, "Organización no encontrada")
    sectors = db.scalars(select(CoverageSector).where(CoverageSector.id.in_(payload.sector_ids))).all() if payload.sector_ids else []
    points = db.scalars(select(EcoPoint).where(EcoPoint.id.in_(payload.ecopoint_ids))).all() if payload.ecopoint_ids else []
    if len(sectors) != len(set(payload.sector_ids)) or len(points) != len(set(payload.ecopoint_ids)):
        raise HTTPException(404, "Uno o más sectores o EcoPuntos no existen")
    # Explicit organization coverage must be sector-linked; never infer from university/address.
    for point in points:
        if not any(point in sector.ecopoints for sector in sectors):
            raise HTTPException(422, f"El EcoPunto {point.name} no está vinculado a ninguno de los sectores seleccionados")
    expected_points = {point.id for sector in sectors for point in sector.ecopoints}
    if not {point.id for point in points}.issubset(expected_points):
        raise HTTPException(422, "Cada EcoPunto seleccionado debe estar vinculado explícitamente a un sector de la organización")
    item.sectors = sectors
    refresh_organization_assignments(db, item)
    db.commit(); db.refresh(item); return _org_read(db, item)


@router.get("/sectors", response_model=list[SectorRead])
def sectors(q: str | None = Query(default=None, max_length=120), active: bool | None = None, db: Session = Depends(get_db), _actor: User = Depends(admin)):
    query = select(CoverageSector)
    if q: query = query.where(or_(CoverageSector.name.ilike(f"%{q.strip()}%"), CoverageSector.locality.ilike(f"%{q.strip()}%"), CoverageSector.city.ilike(f"%{q.strip()}%")))
    if active is not None: query = query.where(CoverageSector.active.is_(active))
    return [_sector_read(item) for item in db.scalars(query.order_by(CoverageSector.city, CoverageSector.locality, CoverageSector.name)).all()]


@router.post("/sectors", response_model=SectorRead, status_code=201)
def create_sector(payload: SectorCreate, db: Session = Depends(get_db), _actor: User = Depends(admin)):
    item = CoverageSector(**payload.model_dump()); db.add(item); db.commit(); db.refresh(item); return _sector_read(item)


@router.patch("/sectors/{sector_id}", response_model=SectorRead)
def update_sector(sector_id: UUID, payload: SectorPatch, db: Session = Depends(get_db), _actor: User = Depends(admin)):
    item = db.get(CoverageSector, sector_id)
    if item is None: raise HTTPException(404, "Sector no encontrado")
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()): raise HTTPException(422, "Los campos del sector no pueden ser null")
    for key, value in changes.items(): setattr(item, key, value)
    for org in item.organizations: refresh_organization_assignments(db, org)
    db.commit(); db.refresh(item); return _sector_read(item)


@router.put("/sectors/{sector_id}/ecopoints", response_model=SectorRead)
def set_sector_ecopoints(sector_id: UUID, payload: SectorPointsUpdate, db: Session = Depends(get_db), _actor: User = Depends(admin)):
    item = db.get(CoverageSector, sector_id)
    if item is None: raise HTTPException(404, "Sector no encontrado")
    points = db.scalars(select(EcoPoint).where(EcoPoint.id.in_(payload.ecopoint_ids))).all() if payload.ecopoint_ids else []
    if len(points) != len(set(payload.ecopoint_ids)): raise HTTPException(404, "Uno o más EcoPuntos no existen")
    item.ecopoints = points
    for org in item.organizations: refresh_organization_assignments(db, org)
    db.commit(); db.refresh(item); return _sector_read(item)


@router.delete("/sectors/{sector_id}", status_code=204)
def delete_sector(sector_id: UUID, db: Session = Depends(get_db), _actor: User = Depends(admin)):
    item = db.get(CoverageSector, sector_id)
    if item is None: raise HTTPException(404, "Sector no encontrado")
    if item.organizations or db.scalar(select(RecyclerAssignment.id).where(RecyclerAssignment.sector_id == item.id).limit(1)):
        raise HTTPException(409, "El sector tiene cobertura o asignaciones históricas; desactívalo para conservar la trazabilidad")
    db.delete(item); db.commit(); return None


@router.get("", response_model=list[RecyclerRead])
def list_recyclers(
    q: str | None = Query(default=None, max_length=120), organization_id: UUID | None = None,
    active: bool | None = None, db: Session = Depends(get_db), _actor: User = Depends(admin),
):
    query = select(User).where(User.role == UserRole.RECYCLER)
    if q: query = query.where(or_(User.full_name.ilike(f"%{q.strip()}%"), User.email.ilike(f"%{q.strip()}%")))
    if active is not None: query = query.where(User.is_active.is_(active))
    users = db.scalars(query.order_by(User.full_name)).all()
    result = [_recycler_read(db, user) for user in users]
    return [item for item in result if item.organization_id == organization_id] if organization_id else result


@router.post("", response_model=RecyclerRead, status_code=201)
def create_recycler(payload: RecyclerCreate, db: Session = Depends(get_db), _actor: User = Depends(admin)):
    email = str(payload.email).lower().strip()
    if by_email(db, email): raise HTTPException(409, "Ya existe una cuenta con ese correo")
    org = db.get(Organization, payload.organization_id) if payload.organization_id else None
    link_type = payload.link_type or (
        RecyclerLinkType.ORGANIZATION if payload.organization_id else RecyclerLinkType.INDEPENDENT
    )
    if payload.organization_id and org is None:
        raise HTTPException(404, "Organización no encontrada")
    if payload.organization_id and org.status != OrganizationStatus.ACTIVE:
        raise HTTPException(422, "La organización debe estar activa para vincular recicladores")
    if link_type == RecyclerLinkType.ORGANIZATION and org is None:
        raise HTTPException(422, "Selecciona una organización para este tipo de vinculación")
    if link_type == RecyclerLinkType.INDEPENDENT and org is not None:
        raise HTTPException(422, "Un reciclador independiente no puede quedar vinculado a una organización")
    user = User(email=email, full_name=payload.full_name, password_hash=hash_password(payload.password), role=UserRole.RECYCLER, university_id=None, is_active=payload.is_active)
    db.add(user); db.flush()
    profile = RecyclerProfile(user_id=user.id, organization_id=org.id if org else None,
        link_type=link_type, phone=payload.phone, document_type=payload.document_type,
        document_number=payload.document_number,
        status=RecyclerProfileStatus.ACTIVE if payload.is_active else RecyclerProfileStatus.SUSPENDED)
    db.add(profile)
    try:
        db.flush()
        if org: refresh_organization_assignments(db, org)
        db.commit()
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(409, "No se pudo crear la cuenta; revisa si el correo ya existe") from exc
    db.refresh(user); return _recycler_read(db, user)


@router.get("/organizations/{organization_id}/recyclers", response_model=list[RecyclerRead])
def organization_recyclers(organization_id: UUID, db: Session = Depends(get_db), _actor: User = Depends(admin)):
    if db.get(Organization, organization_id) is None: raise HTTPException(404, "Organización no encontrada")
    rows = db.scalars(select(User).join(RecyclerProfile).where(User.role == UserRole.RECYCLER, RecyclerProfile.organization_id == organization_id).order_by(User.full_name)).all()
    return [_recycler_read(db, user) for user in rows]


@router.patch("/{recycler_id}", response_model=RecyclerRead)
def update_recycler(recycler_id: UUID, payload: RecyclerPatch, db: Session = Depends(get_db), _actor: User = Depends(admin)):
    user = db.get(User, recycler_id)
    if user is None or user.role != UserRole.RECYCLER: raise HTTPException(404, "Reciclador no encontrado")
    profile = db.get(RecyclerProfile, user.id)
    if profile is None: raise HTTPException(409, "El perfil del reciclador requiere revisión antes de editarlo")
    changes = payload.model_dump(exclude_unset=True)
    if any(changes.get(field) is None for field in ("email", "full_name", "link_type", "is_active") if field in changes):
        raise HTTPException(422, "Correo, nombre, tipo de vínculo y estado no pueden ser null")
    if "email" in changes:
        email = str(changes.pop("email")).strip().lower()
        existing = by_email(db, email)
        if existing is not None and existing.id != user.id: raise HTTPException(409, "Ya existe una cuenta con ese correo")
        user.email = email
    if "full_name" in changes: user.full_name = changes.pop("full_name")
    org_id = changes.pop("organization_id", profile.organization_id)
    link_type = changes.pop("link_type", profile.link_type)
    org = db.get(Organization, org_id) if org_id else None
    if org_id and org is None: raise HTTPException(404, "Organización no encontrada")
    if (link_type == RecyclerLinkType.ORGANIZATION) != bool(org): raise HTTPException(422, "La organización debe coincidir con el tipo de vinculación")
    if org_id != profile.organization_id or link_type != profile.link_type:
        replace_recycler_organization(db, user, profile, org)
    for field in ("phone", "document_type", "document_number"):
        if field in changes: setattr(profile, field, changes[field])
    if "is_active" in changes:
        user.is_active = changes["is_active"]
        profile.status = RecyclerProfileStatus.ACTIVE if user.is_active else RecyclerProfileStatus.SUSPENDED
        if not user.is_active:
            now = datetime.now(UTC)
            grants = db.scalars(select(RecyclerAssignment).where(
                RecyclerAssignment.recycler_id == user.id,
                RecyclerAssignment.status == AssignmentStatus.ACTIVE,
            )).all()
            for grant in grants:
                grant.status = AssignmentStatus.INACTIVE
                grant.ends_at = now
                grant.notes = (grant.notes + " · perfil suspendido") if grant.notes else "Perfil suspendido"
        if profile.organization_id:
            org = db.get(Organization, profile.organization_id)
            if org: refresh_organization_assignments(db, org)
    db.commit(); db.refresh(user); return _recycler_read(db, user)


@router.get("/assignments", response_model=list[AssignmentRead])
def list_assignments(
    organization_id: UUID | None = None, recycler_id: UUID | None = None,
    sector_id: UUID | None = None, university_id: UUID | None = None,
    ecopoint_id: UUID | None = None, state: AssignmentStatus | None = None,
    db: Session = Depends(get_db), actor: User = Depends(get_current_user),
):
    query = select(RecyclerAssignment).order_by(RecyclerAssignment.starts_at.desc())
    if actor.role == UserRole.RECYCLER: query = query.where(RecyclerAssignment.recycler_id == actor.id)
    elif actor.role != UserRole.ADMIN: raise HTTPException(403, "No tienes permisos para consultar asignaciones")
    else:
        if organization_id: query = query.where(RecyclerAssignment.organization_id == organization_id)
        if recycler_id: query = query.where(RecyclerAssignment.recycler_id == recycler_id)
    if sector_id: query = query.where(RecyclerAssignment.sector_id == sector_id)
    if university_id: query = query.where(RecyclerAssignment.university_id == university_id)
    if ecopoint_id: query = query.where(RecyclerAssignment.ecopoint_id == ecopoint_id)
    if state: query = query.where(RecyclerAssignment.status == state)
    return db.scalars(query).all()


@router.post("/assignments", response_model=AssignmentRead, status_code=201)
def create_assignment(payload: AssignmentCreate, db: Session = Depends(get_db), _actor: User = Depends(admin)):
    user = db.get(User, payload.recycler_id)
    profile = db.get(RecyclerProfile, payload.recycler_id)
    if user is None or user.role != UserRole.RECYCLER or profile is None: raise HTTPException(404, "Reciclador no encontrado")
    if profile.link_type != RecyclerLinkType.INDEPENDENT: raise HTTPException(422, "Las asignaciones de un reciclador vinculado se derivan de la cobertura de su organización")
    if not user.is_active or profile.status != RecyclerProfileStatus.ACTIVE: raise HTTPException(422, "No se puede autorizar un perfil suspendido")
    if not any((payload.sector_id, payload.university_id, payload.ecopoint_id)): raise HTTPException(422, "La asignación requiere al menos un ámbito")
    sector = db.get(CoverageSector, payload.sector_id) if payload.sector_id else None
    if payload.sector_id and sector is None: raise HTTPException(404, "Sector no encontrado")
    point = db.get(EcoPoint, payload.ecopoint_id) if payload.ecopoint_id else None
    if payload.ecopoint_id and point is None: raise HTTPException(404, "EcoPunto no encontrado")
    if point and sector and point not in sector.ecopoints: raise HTTPException(422, "El EcoPunto no está vinculado al sector seleccionado")
    university_id = payload.university_id or (point.university_id if point else None)
    if point and university_id != point.university_id: raise HTTPException(422, "El EcoPunto no pertenece a la universidad indicada")
    if university_id:
        university = db.get(University, university_id)
        if university is None: raise HTTPException(404, "Universidad no encontrada")
    if payload.ends_at and payload.starts_at and payload.ends_at <= payload.starts_at: raise HTTPException(422, "La vigencia final debe ser posterior al inicio")
    now = datetime.now(UTC)
    duplicates = db.scalars(select(RecyclerAssignment).where(
        RecyclerAssignment.recycler_id == user.id, RecyclerAssignment.origin == "DIRECT",
        RecyclerAssignment.status == AssignmentStatus.ACTIVE,
        RecyclerAssignment.sector_id == payload.sector_id,
        RecyclerAssignment.university_id == university_id,
        RecyclerAssignment.ecopoint_id == payload.ecopoint_id,
    )).all()
    for duplicate in duplicates:
        if duplicate.ends_at is None or duplicate.ends_at >= now:
            raise HTTPException(409, "La asignación directa activa ya existe")
        # Close an expired row logically before a replacement so the old SQLite
        # uniqueness rule can coexist with the preserved history.
        duplicate.status = AssignmentStatus.INACTIVE
    item = RecyclerAssignment(recycler_id=user.id, sector_id=payload.sector_id,
        university_id=university_id, ecopoint_id=payload.ecopoint_id,
        starts_at=payload.starts_at or datetime.now(UTC), ends_at=payload.ends_at,
        status=payload.status, notes=payload.notes, origin="DIRECT")
    db.add(item); db.commit(); db.refresh(item); return item


@router.patch("/assignments/{assignment_id}", response_model=AssignmentRead)
def update_assignment(assignment_id: UUID, payload: AssignmentPatch, db: Session = Depends(get_db), _actor: User = Depends(admin)):
    item = db.get(RecyclerAssignment, assignment_id)
    if item is None: raise HTTPException(404, "Asignación no encontrada")
    changes = payload.model_dump(exclude_unset=True)
    if any(changes.get(field) is None for field in ("starts_at", "status") if field in changes):
        raise HTTPException(422, "Inicio y estado no pueden ser null")
    start = changes.get("starts_at", item.starts_at); end = changes.get("ends_at", item.ends_at)
    if end and start and end <= start: raise HTTPException(422, "La vigencia final debe ser posterior al inicio")
    if item.origin == "AUTOMATIC" and "status" in changes:
        raise HTTPException(422, "El estado de una asignación heredada se administra desde la cobertura de la organización")
    if item.origin == "DIRECT" and changes.get("status") == AssignmentStatus.ACTIVE:
        user = db.get(User, item.recycler_id); profile = db.get(RecyclerProfile, item.recycler_id)
        if not user or not user.is_active or not profile or profile.status != RecyclerProfileStatus.ACTIVE or profile.link_type != RecyclerLinkType.INDEPENDENT:
            raise HTTPException(422, "Solo se puede activar una asignación directa para un perfil independiente y activo")
    for key, value in changes.items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item


@router.get("/me", response_model=RecyclerRead)
def my_profile(db: Session = Depends(get_db), actor: User = Depends(recycler)):
    return _recycler_read(db, actor)


@router.get("/me/dashboard", response_model=RecyclerDashboardRead)
def my_dashboard(db: Session = Depends(get_db), actor: User = Depends(recycler)):
    profile = _recycler_read(db, actor)
    assignments = db.scalars(select(RecyclerAssignment).where(RecyclerAssignment.recycler_id == actor.id).order_by(RecyclerAssignment.starts_at.desc())).all()
    assignment_reads = []
    for item in assignments:
        sector = db.get(CoverageSector, item.sector_id) if item.sector_id else None
        university = db.get(University, item.university_id) if item.university_id else None
        point = db.get(EcoPoint, item.ecopoint_id) if item.ecopoint_id else None
        assignment_reads.append(AssignmentRead.model_validate(item).model_copy(update={
            "sector_name": sector.name if sector else None,
            "university_name": university.name if university else None,
            "ecopoint_name": point.name if point else None,
        }))
    collections = db.scalars(select(Collection).where(Collection.recycler_id == actor.id).order_by(Collection.created_at.desc())).all()
    total = sum((item.weight_kg for item in collections), start=0)
    material_rows = db.execute(select(func.coalesce(Material.name, Compartment.label), func.sum(Collection.weight_kg))
        .join(Collection.compartment).outerjoin(Material, func.coalesce(Collection.material_id, Compartment.material_id) == Material.id)
        .where(Collection.recycler_id == actor.id)
        .group_by(func.coalesce(Material.name, Compartment.label)).order_by(func.coalesce(Material.name, Compartment.label))).all()
    return {"profile": profile, "assignments": assignment_reads, "collections": collections,
            "recovered_weight_kg": total, "collection_count": len(collections),
            "material_weights": [{"material_name": label, "weight_kg": weight} for label, weight in material_rows],
            "as_of": datetime.now(UTC)}


@router.get("/{recycler_id}/assignments", response_model=list[AssignmentRead])
def recycler_assignments(recycler_id: UUID, db: Session = Depends(get_db), _actor: User = Depends(admin)):
    return db.scalars(select(RecyclerAssignment).where(RecyclerAssignment.recycler_id == recycler_id).order_by(RecyclerAssignment.starts_at.desc())).all()

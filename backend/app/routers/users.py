from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.dependencies import get_current_user, require_roles
from app.models import University, User, UserRole
from app.repositories.users import by_email, list_visible_users, visible_user
from app.schemas.api import UserAdminCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Usuarios"])
user_manager = require_roles(UserRole.ADMIN)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("", response_model=list[UserRead])
def list_users(
    university_id: UUID | None = None,
    role: UserRole | None = None,
    active: bool | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    actor: User = Depends(user_manager),
    db: Session = Depends(get_db),
) -> list[User]:
    return list_visible_users(
        db, actor, university_id=university_id, role=role, active=active,
        offset=offset, limit=limit,
    )


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: UUID,
    actor: User = Depends(user_manager),
    db: Session = Depends(get_db),
) -> User:
    user = visible_user(db, user_id, actor)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserAdminCreate, actor: User = Depends(user_manager), db: Session = Depends(get_db)) -> User:
    if payload.role == UserRole.ADMIN:
        if payload.university_id is not None:
            raise HTTPException(status_code=422, detail="El administrador de plataforma no puede pertenecer a una universidad")
        university = None
    else:
        if payload.university_id is None:
            raise HTTPException(status_code=422, detail="La universidad es obligatoria para usuarios institucionales")
        university = db.get(University, payload.university_id)
        if university is None:
            raise HTTPException(status_code=404, detail="Universidad no encontrada")
        if not university.active:
            raise HTTPException(status_code=422, detail="No se pueden crear usuarios en una universidad inactiva")

    email = str(payload.email).strip().lower()
    if by_email(db, email):
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")
    user = User(
        email=email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        university=university,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        if by_email(db, email) is not None:
            raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo") from exc
        raise HTTPException(status_code=409, detail="No se pudo crear el usuario con esos datos") from exc
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    actor: User = Depends(user_manager),
    db: Session = Depends(get_db),
) -> User:
    user = visible_user(db, user_id, actor)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="No hay datos para actualizar")
    if any(changes.get(field) is None for field in ("email", "full_name", "role", "is_active") if field in changes):
        raise HTTPException(status_code=422, detail="Los campos enviados no pueden ser null")
    if "email" in changes:
        email = str(changes["email"]).strip().lower()
        existing = by_email(db, email)
        if existing is not None and existing.id != user.id:
            raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")
        changes["email"] = email

    if {"role", "university_id"}.intersection(changes):
        role = changes.get("role", user.role)
        university_id = changes.get("university_id", user.university_id)
        if role is None:
            raise HTTPException(status_code=422, detail="El rol no puede ser null")
        if role == UserRole.ADMIN:
            if "university_id" in changes and university_id is not None:
                raise HTTPException(status_code=422, detail="El administrador global no pertenece a una universidad")
            user.role = role
            user.university = None
        else:
            if university_id is None:
                raise HTTPException(status_code=422, detail="La universidad es obligatoria para usuarios institucionales")
            university = db.get(University, university_id)
            if university is None:
                raise HTTPException(status_code=404, detail="Universidad no encontrada")
            if not university.active:
                raise HTTPException(status_code=422, detail="No se pueden asignar usuarios a una universidad inactiva")
            user.role = role
            user.university = university

    for field, value in changes.items():
        if field not in {"role", "university_id"}:
            setattr(user, field, value)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo actualizar el usuario por sus relaciones o restricciones") from exc
    return user

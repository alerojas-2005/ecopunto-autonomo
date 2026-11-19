import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, UserRole
from app.repositories.users import by_email
from app.schemas.api import BootstrapAdminRequest, LoginRequest, RegisterRequest, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    email = str(payload.email).lower()
    if by_email(db, email):
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")
    user = User(email=email, full_name=payload.full_name, password_hash=hash_password(payload.password), role=UserRole.CITIZEN)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = by_email(db, str(payload.email).lower())
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos", headers={"WWW-Authenticate": "Bearer"})
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/bootstrap-admin", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(
    payload: BootstrapAdminRequest,
    x_bootstrap_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    configured_token = settings.bootstrap_admin_token
    expected_token = configured_token.get_secret_value() if configured_token else ""
    if len(expected_token) < 32 or x_bootstrap_token is None or not secrets.compare_digest(
        x_bootstrap_token, expected_token
    ):
        raise HTTPException(status_code=404, detail="No encontrado")
    # Serialize bootstrap attempts on SQLite so concurrent requests cannot create two first admins.
    if settings.database_url.startswith("sqlite"):
        db.execute(text("BEGIN IMMEDIATE"))
    if db.scalar(select(User.id).where(User.role == UserRole.ADMIN).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="El administrador inicial ya fue creado")
    email = str(payload.email).lower()
    if by_email(db, email):
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")
    user = User(email=email, full_name=payload.full_name, password_hash=hash_password(payload.password), role=UserRole.ADMIN)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise
    return user

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.dependencies import get_current_user, require_roles
from app.models import User, UserRole
from app.repositories.users import by_email
from app.schemas.api import UserAdminCreate, UserRead

router = APIRouter(prefix="/users", tags=["Usuarios"])
admin_only = require_roles(UserRole.ADMIN)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserAdminCreate, _admin: User = Depends(admin_only), db: Session = Depends(get_db)) -> User:
    email = str(payload.email).lower()
    if by_email(db, email):
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")
    user = User(email=email, full_name=payload.full_name, password_hash=hash_password(payload.password), role=payload.role)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise
    return user

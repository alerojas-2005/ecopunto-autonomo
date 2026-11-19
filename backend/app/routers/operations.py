from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import Alert, AlertStatus, Collection, User, UserRole
from app.repositories.operations import get_or_404, list_alerts, visible_collections
from app.schemas.api import AlertRead, CollectionCreate, CollectionRead
from app.services.collections import register_collection

router = APIRouter(tags=["Alertas y recolecciones"])
staff_roles = (UserRole.ADMIN, UserRole.RECYCLER)
staff_only = require_roles(*staff_roles)
recycler_only = require_roles(UserRole.RECYCLER)


@router.get("/alerts", response_model=list[AlertRead])
def get_alerts(_user: User = Depends(staff_only), db: Session = Depends(get_db)):
    return list_alerts(db)


@router.patch("/alerts/{alert_id}/resolve", response_model=AlertRead)
def resolve_alert(alert_id: UUID, _user: User = Depends(staff_only), db: Session = Depends(get_db)):
    alert = get_or_404(db, Alert, alert_id, "Alerta")
    if alert.status == AlertStatus.ACTIVE:
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(UTC)
        db.commit()
        db.refresh(alert)
    return alert


@router.post("/collections", response_model=CollectionRead, status_code=status.HTTP_201_CREATED)
def create_collection(payload: CollectionCreate, user: User = Depends(recycler_only), db: Session = Depends(get_db)):
    return register_collection(db, user, payload)


@router.get("/collections", response_model=list[CollectionRead])
def get_collections(user: User = Depends(staff_only), db: Session = Depends(get_db)):
    return visible_collections(db, user)


@router.get("/collections/{collection_id}", response_model=CollectionRead)
def get_collection(collection_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    collection = get_or_404(db, Collection, collection_id, "Recolección")
    if user.role == UserRole.CITIZEN or (user.role == UserRole.RECYCLER and collection.recycler_id != user.id):
        raise HTTPException(status_code=404, detail="Recolección no encontrada")
    return collection

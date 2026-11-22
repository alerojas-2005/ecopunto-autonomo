from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import University
from app.schemas.api import UniversityRegistrationOption

router = APIRouter(prefix="/universities", tags=["Universidades"])


@router.get("/registration-options", response_model=list[UniversityRegistrationOption])
def registration_options(db: Session = Depends(get_db)) -> list[University]:
    query = (
        select(University)
        .where(University.active.is_(True), University.public_registration_enabled.is_(True))
        .order_by(University.name)
    )
    return list(db.scalars(query).all())

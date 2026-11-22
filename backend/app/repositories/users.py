from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User


def by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def by_id(db: Session, user_id: UUID) -> User | None:
    return db.get(User, user_id)

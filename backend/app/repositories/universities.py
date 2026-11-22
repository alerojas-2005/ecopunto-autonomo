from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import University, User, UserRole


def list_visible_universities(
    db: Session, user: User, *, active: bool | None = None
) -> list[University]:
    query = select(University)
    if user.role != UserRole.ADMIN:
        query = query.where(University.id == user.university_id)
    if active is not None:
        query = query.where(University.active.is_(active))
    return db.scalars(query.order_by(University.name)).all()


def visible_university(db: Session, university_id: UUID, user: User) -> University | None:
    query = select(University).where(University.id == university_id)
    if user.role != UserRole.ADMIN:
        query = query.where(University.id == user.university_id)
    return db.scalar(query)

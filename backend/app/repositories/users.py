from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User, UserRole


def by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def by_id(db: Session, user_id: UUID) -> User | None:
    return db.get(User, user_id)


def visible_user(db: Session, user_id: UUID, actor: User) -> User | None:
    if actor.role != UserRole.ADMIN:
        return None
    query = select(User).where(User.id == user_id)
    return db.scalar(query)


def list_visible_users(
    db: Session,
    actor: User,
    *,
    university_id: UUID | None = None,
    role: UserRole | None = None,
    active: bool | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[User]:
    query = select(User)
    if actor.role != UserRole.ADMIN:
        return []
    if university_id is not None:
        query = query.where(User.university_id == university_id)
    if role is not None:
        query = query.where(User.role == role)
    if active is not None:
        query = query.where(User.is_active.is_(active))
    return db.scalars(query.order_by(User.created_at.desc()).offset(offset).limit(limit)).all()

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (AssignmentStatus, CoverageSector, EcoPoint, Organization,
                        OrganizationStatus, RecyclerAssignment, RecyclerLinkType, RecyclerProfile,
                        RecyclerProfileStatus, User, UserRole)


def active_coverage(org: Organization, user: User, profile: RecyclerProfile) -> bool:
    return (
        org.status == OrganizationStatus.ACTIVE
        and user.is_active
        and profile.status == RecyclerProfileStatus.ACTIVE
    )


def refresh_organization_assignments(db: Session, organization: Organization) -> None:
    """Replace an organization's current automatic grants; keep old rows as history."""
    now = datetime.now(UTC)
    old_rows = db.scalars(select(RecyclerAssignment).where(
        RecyclerAssignment.organization_id == organization.id,
        RecyclerAssignment.origin == "AUTOMATIC",
        RecyclerAssignment.status == AssignmentStatus.ACTIVE,
    )).all()
    for old in old_rows:
        old.status = AssignmentStatus.INACTIVE
        old.ends_at = now
        old.notes = (old.notes + " · cobertura reemplazada") if old.notes else "Cobertura reemplazada"

    members = db.execute(
        select(User, RecyclerProfile)
        .join(RecyclerProfile, RecyclerProfile.user_id == User.id)
        .where(User.role == UserRole.RECYCLER, RecyclerProfile.organization_id == organization.id)
    ).all()
    sectors = [sector for sector in organization.sectors if sector.active]
    for user, profile in members:
        is_authorized = active_coverage(organization, user, profile)
        if not is_authorized:
            # Revoked rows above retain the event in history. Do not create grants for
            # suspended members/organizations; this also avoids duplicate suspended scopes.
            continue
        for sector in sectors:
            points = [point for point in sector.ecopoints if point.active]
            if points:
                for point in points:
                    db.add(RecyclerAssignment(
                        recycler_id=user.id, organization_id=organization.id,
                        sector_id=sector.id, university_id=point.university_id,
                        ecopoint_id=point.id, starts_at=now,
                        status=AssignmentStatus.ACTIVE,
                        origin="AUTOMATIC", notes="Cobertura heredada de la organización",
                    ))
            else:
                db.add(RecyclerAssignment(
                    recycler_id=user.id, organization_id=organization.id,
                    sector_id=sector.id, starts_at=now,
                    status=AssignmentStatus.ACTIVE,
                    origin="AUTOMATIC", notes="Sector heredado; sin EcoPuntos vinculados",
                ))


def replace_recycler_organization(
    db: Session, user: User, profile: RecyclerProfile, organization: Organization | None
) -> None:
    now = datetime.now(UTC)
    existing = db.scalars(select(RecyclerAssignment).where(
        RecyclerAssignment.recycler_id == user.id,
        RecyclerAssignment.status == AssignmentStatus.ACTIVE,
    )).all()
    for item in existing:
        item.status = AssignmentStatus.INACTIVE
        item.ends_at = now
        item.notes = (item.notes + " · vinculación modificada") if item.notes else "Vinculación modificada"
    profile.organization_id = organization.id if organization else None
    profile.link_type = RecyclerLinkType.ORGANIZATION if organization else RecyclerLinkType.INDEPENDENT
    if organization:
        # Test and request sessions disable autoflush. Persist the membership change
        # before refresh_organization_assignments queries its member list.
        db.flush()
        refresh_organization_assignments(db, organization)

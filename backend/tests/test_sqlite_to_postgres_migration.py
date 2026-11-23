from datetime import UTC, datetime
from decimal import Decimal
import hashlib
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, func, inspect, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.postgres_integrity import POSTGRES_INTEGRITY_DDL, install_postgres_integrity_triggers
from app.core.database import Base
from app.models import (
    Alert, AlertStatus, AlertType, AssignmentStatus, Collection, Compartment,
    Deposit, EcoPoint, Material, Organization, OrganizationStatus, OrganizationType,
    PointTransaction, RecyclerAssignment, RecyclerLinkType, RecyclerProfile,
    RecyclerProfileStatus, TransactionType, University, User, UserRole,
)
from scripts.migrate_sqlite_to_postgres import MigrationError, _source_engine, migrate, preflight


def _sqlite_engine(url: str):
    engine = create_engine(url, poolclass=StaticPool) if url == "sqlite://" else create_engine(url)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _make_database(path):
    engine = _sqlite_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(engine)
    university_id, org_id, citizen_id, recycler_id = uuid4(), uuid4(), uuid4(), uuid4()
    point_id, material_id, compartment_id, deposit_id = uuid4(), uuid4(), uuid4(), uuid4()
    now = datetime(2026, 11, 22, 12, 30, tzinfo=UTC)
    with Session(engine) as db:
        university = University(id=university_id, name="Universidad migrada", slug="uni-migrada", city="Bogotá", campus_name="Sede", active=True, public_registration_enabled=True)
        org = Organization(id=org_id, name="Asociación", type=OrganizationType.ASSOCIATION, city="Bogotá", status=OrganizationStatus.ACTIVE)
        citizen = User(id=citizen_id, email="citizen@example.com", full_name="Ciudadana", password_hash="$argon2id$hash-citizen", role=UserRole.CITIZEN, university=university, created_at=now)
        recycler = User(id=recycler_id, email="recycler@example.com", full_name="Reciclador", password_hash="$argon2id$hash-recycler", role=UserRole.RECYCLER, university=university, created_at=now)
        material = Material(id=material_id, name="PET migrado", points_per_gram=Decimal("0.2500"), active=True)
        point = EcoPoint(id=point_id, code="MIG-01", name="Punto migrado", address="Bogotá", active=True, university=university, created_at=now)
        compartment = Compartment(id=compartment_id, ecopoint=point, material=material, label="PET", capacity_kg=Decimal("20.000"), current_kg=Decimal("18.375"), fill_threshold_pct=80, active=True)

        # RecyclerAssignment stores scalar FK values and has no ORM relationships
        # for these four parents, so persist and verify them before adding a grant.
        db.add_all([university, org, citizen, recycler, material, point, compartment])
        db.flush()
        assert recycler.id == recycler_id and db.get(User, recycler_id) is not None
        assert org.id == org_id and db.get(Organization, org_id) is not None
        assert university.id == university_id and db.get(University, university_id) is not None
        assert point.id == point_id and db.get(EcoPoint, point_id) is not None
        profile = RecyclerProfile(user=recycler, organization_id=org_id, link_type=RecyclerLinkType.ORGANIZATION, status=RecyclerProfileStatus.ACTIVE, linked_at=now)
        db.add(profile)
        db.flush()
        assignment = RecyclerAssignment(recycler_id=recycler_id, organization_id=org_id, origin="AUTOMATIC", university_id=university_id, ecopoint_id=point_id, starts_at=now, status=AssignmentStatus.ACTIVE)
        deposit = Deposit(id=deposit_id, citizen=citizen, ecopoint=point, compartment=compartment, material=material, weight_g=625, factor_applied=Decimal("0.2500"), points_awarded=Decimal("156.2500"), created_at=now)
        transaction = PointTransaction(user=citizen, deposit=deposit, type=TransactionType.EARN, amount=Decimal("156.2500"), description="Depósito histórico", created_at=now)
        collection = Collection(ecopoint=point, compartment=compartment, recycler=recycler, material_id=material_id, weight_kg=Decimal("0.625"), created_at=now, notes="Historial")
        alert = Alert(compartment=compartment, type=AlertType.FILL_THRESHOLD, status=AlertStatus.RESOLVED, message="Alerta histórica", created_at=now, resolved_at=now)
        db.add_all([assignment, deposit, transaction, collection, alert])
        db.commit()
    populated = {
        "users": 2, "organizations": 1, "universities": 1, "materials": 1,
        "ecopoints": 1, "compartments": 1, "recycler_profiles": 1,
        "recycler_assignments": 1, "deposits": 1, "point_transactions": 1,
        "collections": 1, "alerts": 1,
    }
    counts = {table.name: populated.get(table.name, 0) for table in Base.metadata.sorted_tables}
    return engine, counts


def test_sqlite_copy_preserves_all_records_and_is_idempotent(tmp_path):
    source, counts = _make_database(tmp_path / "source.db")
    target = _sqlite_engine("sqlite://")
    try:
        first = migrate(source, target, require_postgres=False)
        second = migrate(source, target, require_postgres=False)
        assert first == counts
        assert second == counts
        with Session(target) as db:
            recycler = db.scalar(select(User).where(User.role == UserRole.RECYCLER))
            assert recycler.password_hash == "$argon2id$hash-recycler"
            assert recycler.recycler_profile.organization_id == db.scalar(select(Organization.id))
            assert db.scalar(select(Deposit)).factor_applied == Decimal("0.2500")
            assert db.scalar(select(Collection)).weight_kg == Decimal("0.625")
            assert db.scalar(select(PointTransaction)).deposit_id is not None
        assert inspect(target).get_table_names() == sorted(Base.metadata.tables)
        with target.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    finally:
        source.dispose()
        target.dispose()


def test_readonly_preflight_checks_schema_constraints_and_counts(tmp_path):
    source, counts = _make_database(tmp_path / "preflight.db")
    try:
        assert preflight(source) == counts
        with source.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA integrity_check").scalar_one() == "ok"
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    finally:
        source.dispose()


def test_preflight_accepts_university_admin_check_and_requires_university(tmp_path):
    source, counts = _make_database(tmp_path / "university-admin-check.db")
    try:
        with source.begin() as connection:
            university_id = connection.exec_driver_sql(
                "SELECT id FROM universities LIMIT 1"
            ).scalar_one()
            connection.exec_driver_sql(
                "INSERT INTO users "
                "(id, email, full_name, password_hash, role, university_id, is_active, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    uuid4().hex,
                    "legacy-admin@example.com",
                    "Administradora universitaria histórica",
                    "$argon2id$legacy-admin-hash",
                    "UNIVERSITY_ADMIN",
                    university_id,
                    1,
                    "2026-11-22 12:30:00",
                ),
            )
            counts["users"] += 1

            # The persisted legacy role is valid only when linked to a university.
            with pytest.raises(IntegrityError):
                connection.exec_driver_sql(
                    "INSERT INTO users "
                    "(id, email, full_name, password_hash, role, university_id, is_active, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        uuid4().hex,
                        "legacy-admin-without-university@example.com",
                        "Administradora sin universidad",
                        "$argon2id$legacy-admin-hash",
                        "UNIVERSITY_ADMIN",
                        None,
                        1,
                        "2026-11-22 12:30:00",
                    ),
                )

        assert preflight(source) == counts
    finally:
        source.dispose()


def test_preflight_uses_sqlite_pragma_delete_action_for_recycler_assignment(tmp_path):
    source, counts = _make_database(tmp_path / "fk-action.db")
    try:
        with source.connect() as connection:
            fk = next(
                row for row in connection.exec_driver_sql(
                    'PRAGMA foreign_key_list("recycler_assignments")'
                )
                if row[3] == "organization_id"
            )
            assert fk[2:5] == ("organizations", "organization_id", "id")
            assert fk[5] == "NO ACTION"  # ON UPDATE
            assert fk[6] == "RESTRICT"   # ON DELETE
        assert preflight(source) == counts
    finally:
        source.dispose()


def test_source_engine_resolves_relative_path_readonly_on_windows_and_other_platforms(tmp_path, monkeypatch):
    absolute_path = tmp_path / "relative-source.db"
    writable_setup, counts = _make_database(absolute_path)
    writable_setup.dispose()
    original_hash = hashlib.sha256(absolute_path.read_bytes()).hexdigest()

    monkeypatch.chdir(tmp_path)
    source = _source_engine(Path("relative-source.db"))
    try:
        assert preflight(source) == counts
        with pytest.raises(OperationalError):
            with source.begin() as connection:
                connection.exec_driver_sql("CREATE TABLE must_not_be_created (id INTEGER)")
    finally:
        source.dispose()

    assert hashlib.sha256(absolute_path.read_bytes()).hexdigest() == original_hash


def test_migration_refuses_partial_or_different_destination_without_overwriting(tmp_path):
    source, _ = _make_database(tmp_path / "source.db")
    target = _sqlite_engine("sqlite://")
    try:
        Base.metadata.create_all(target)
        with target.begin() as connection:
            connection.execute(User.__table__.insert(), {
                "id": uuid4(), "email": "different@example.com", "full_name": "Other",
                "password_hash": "keep-me", "role": "ADMIN", "university_id": None,
                "is_active": True, "created_at": datetime.now(UTC),
            })
        with pytest.raises(MigrationError, match="datos diferentes o parciales"):
            migrate(source, target, require_postgres=False)
        with target.connect() as connection:
            assert connection.scalar(select(func.count()).select_from(User.__table__)) == 1
    finally:
        source.dispose()
        target.dispose()


def test_postgres_guards_cover_sqlite_business_trigger_rules():
    ddl = "\n".join(POSTGRES_INTEGRITY_DDL)
    for rule in (
        "ecopunto_guard_deposit_resource", "ecopunto_guard_collection_authorization",
        "ecopunto_guard_transaction_owner", "ecopunto_guard_user_history",
        "ecopunto_guard_ecopoint_history", "ecopunto_guard_compartment_history",
        "ecopunto_guard_deposit_owner_history", "IS NOT DISTINCT FROM",
        "ra.status = 'ACTIVE'", "o.status = 'ACTIVE'",
    ):
        assert rule in ddl
    engine = _sqlite_engine("sqlite://")
    try:
        install_postgres_integrity_triggers(engine)
    finally:
        engine.dispose()

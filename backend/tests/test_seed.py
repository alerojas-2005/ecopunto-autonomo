from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app import seed as seed_module
from app.core.database import Base
from app.models import (
    Alert, Collection, Compartment, Deposit, EcoPoint, Material,
    PointTransaction, University, User, UserRole,
)


def test_seed_creates_catalog_for_all_existing_universities_and_is_idempotent(monkeypatch):
    test_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=test_engine)
    test_sessions = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(seed_module, "engine", test_engine)
    monkeypatch.setattr(seed_module, "SessionLocal", test_sessions)

    with test_sessions() as db:
        universities = [University(
            id=uuid4(), name=f"Universidad {i}", slug=f"universidad-{i}",
            city="Bogota D.C.", campus_name="Sede principal",
            active=True, public_registration_enabled=True,
        ) for i in range(32)]
        preserved_user = User(
            id=uuid4(), email="existing@example.test", full_name="Existing",
            password_hash="hash-preserved", role=UserRole.CITIZEN, university=universities[0],
        )
        db.add_all([*universities, preserved_user])
        db.commit()
        user_id, password_hash = preserved_user.id, preserved_user.password_hash

    seed_module.seed()
    seed_module.seed()

    with test_sessions() as db:
        assert db.scalar(select(func.count()).select_from(University)) == 32
        assert db.scalar(select(func.count()).select_from(EcoPoint)) == 32
        assert db.scalar(select(func.count()).select_from(Material)) == 7
        assert db.scalar(select(func.count()).select_from(Compartment)) == 256
        assert db.scalar(select(func.count()).select_from(User)) == 1
        for model in (Deposit, PointTransaction, Alert, Collection):
            assert db.scalar(select(func.count()).select_from(model)) == 0
        preserved = db.get(User, user_id)
        assert preserved.password_hash == password_hash

        expected = {
            "Aluminio": Decimal("0.50"), "PET": Decimal("0.25"),
            "Otros plásticos": Decimal("0.20"), "Cartón": Decimal("0.10"),
            "Papel": Decimal("0.10"), "Tetra Pak": Decimal("0.08"),
            "Vidrio": Decimal("0.05"),
        }
        assert {m.name: Decimal(m.points_per_gram) for m in db.scalars(select(Material))} == expected
        points = db.scalars(select(EcoPoint)).all()
        assert {p.university_id for p in points} == {u.id for u in db.scalars(select(University))}
        assert len({p.code for p in points}) == 32
        assert all(p.active and "simulado" in p.name.casefold() for p in points)
        for point in points:
            bins = db.scalars(select(Compartment).where(Compartment.ecopoint_id == point.id)).all()
            assert len(bins) == 8
            assert len({b.material_id for b in bins}) == 8
            unknown = [b for b in bins if b.material_id is None]
            assert len(unknown) == 1 and unknown[0].label == "No identificados"
            assert all(b.current_kg == Decimal("0.000") and b.active for b in bins)
            assert all(b.capacity_kg == Decimal("25.000") and b.fill_threshold_pct == 80 for b in bins)

    test_engine.dispose()


def test_seed_refuses_to_create_duplicate_ecopoints(monkeypatch):
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=test_engine)
    test_sessions = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(seed_module, "engine", test_engine)
    monkeypatch.setattr(seed_module, "SessionLocal", test_sessions)
    with test_sessions() as db:
        university = University(
            name="U", slug="u", city="Bogota", campus_name="Sede principal",
            active=True, public_registration_enabled=True,
        )
        db.add(university)
        db.flush()
        db.add_all([
            EcoPoint(university=university, code="ONE", name="One", address="Simulada", active=True),
            EcoPoint(university=university, code="TWO", name="Two", address="Simulada", active=True),
        ])
        db.commit()
    with pytest.raises(RuntimeError, match="mas de un EcoPunto"):
        seed_module.seed()
    test_engine.dispose()

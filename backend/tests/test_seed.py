from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import seed as seed_module
from app.models import Compartment, EcoPoint, Material, University


def test_seed_is_idempotent_and_scopes_ecopoint_to_legacy_university(monkeypatch):
    test_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    test_sessions = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(seed_module, "engine", test_engine)
    monkeypatch.setattr(seed_module, "SessionLocal", test_sessions)

    seed_module.seed()
    seed_module.seed()

    with test_sessions() as db:
        university = db.scalar(select(University).where(
            University.slug == "universidad-legado-pendiente"
        ))
        assert university is not None
        assert university.active is True
        assert university.public_registration_enabled is False
        assert len(db.scalars(select(University)).all()) == 1
        assert len(db.scalars(select(Material)).all()) == 2
        ecopoints = db.scalars(select(EcoPoint)).all()
        assert len(ecopoints) == 1
        assert ecopoints[0].university_id == university.id
        assert len(db.scalars(select(Compartment)).all()) == 2

    test_engine.dispose()

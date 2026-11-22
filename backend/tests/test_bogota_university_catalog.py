import importlib.util
from pathlib import Path

from sqlalchemy import func, select

from app.models import Alert, Collection, Compartment, Deposit, EcoPoint, Material, PointTransaction, University, User


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "load_bogota_universities.py"
SPEC = importlib.util.spec_from_file_location("load_bogota_universities", SCRIPT_PATH)
LOADER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(LOADER)


def test_catalog_load_is_idempotent_and_creates_only_universities(db_session):
    count = LOADER.load_universities(db_session)
    db_session.commit()
    initial = db_session.scalars(select(University).order_by(University.slug)).all()
    initial_ids = {university.slug: university.id for university in initial}

    assert count == len(LOADER.BOGOTA_UNIVERSITIES)
    assert len(initial) == len(LOADER.BOGOTA_UNIVERSITIES)
    assert {university.name for university in initial} == set(LOADER.BOGOTA_UNIVERSITIES)
    assert all(university.city == "Bogotá D.C." for university in initial)
    assert all(university.campus_name == "Bogotá D.C." for university in initial)
    assert all(university.active for university in initial)
    assert all(not university.public_registration_enabled for university in initial)

    assert LOADER.load_universities(db_session) == 0
    db_session.commit()
    assert {u.slug: u.id for u in db_session.scalars(select(University)).all()} == initial_ids

    for model in (User, EcoPoint, Compartment, Deposit, PointTransaction, Alert, Collection, Material):
        assert db_session.scalar(select(func.count()).select_from(model)) == 0

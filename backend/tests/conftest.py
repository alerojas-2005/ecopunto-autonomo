import os
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["JWT_SECRET_KEY"] = "pytest-only-secret-that-is-more-than-32-characters"
os.environ["CORS_ORIGINS"] = '["http://localhost:5173"]'

from app import models  # noqa: E402,F401
from app.core.database import Base, get_db  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Compartment, EcoPoint, Material, University, User, UserRole  # noqa: E402

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db_session():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client(db_session):
    app.state.engine = test_engine

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def demo(db_session):
    university = University(name="Universidad de Prueba", slug="universidad-prueba", city="Bogotá", campus_name="Sede principal", active=True, public_registration_enabled=True)
    citizen = User(id=uuid4(), email="citizen@example.test", full_name="Ciudadana Prueba", password_hash=hash_password("StrongPassword123!"), role=UserRole.CITIZEN, university=university)
    other_citizen = User(id=uuid4(), email="other@example.test", full_name="Otra Persona", password_hash=hash_password("StrongPassword123!"), role=UserRole.CITIZEN, university=university)
    admin = User(id=uuid4(), email="admin@example.test", full_name="Admin Prueba", password_hash=hash_password("StrongPassword123!"), role=UserRole.ADMIN)
    recycler = User(id=uuid4(), email="recycler@example.test", full_name="Reciclador Prueba", password_hash=hash_password("StrongPassword123!"), role=UserRole.RECYCLER, university=university)
    aluminum = Material(id=uuid4(), name="Aluminio", points_per_gram=Decimal("0.50"), active=True)
    pet = Material(id=uuid4(), name="PET", points_per_gram=Decimal("0.25"), active=True)
    point = EcoPoint(id=uuid4(), code="TEST-01", name="EcoPunto Prueba", address="Bogotá", active=True, university=university)
    compartment = Compartment(id=uuid4(), ecopoint=point, material=pet, label="PET", capacity_kg=Decimal("20.000"), current_kg=Decimal("19.000"), fill_threshold_pct=80, active=True)
    aluminum_compartment = Compartment(id=uuid4(), ecopoint=point, material=aluminum, label="Aluminio", capacity_kg=Decimal("20.000"), current_kg=Decimal("0.000"), fill_threshold_pct=80, active=True)
    db_session.add_all([university, citizen, other_citizen, admin, recycler, aluminum, pet, point, compartment, aluminum_compartment])
    db_session.commit()
    return {"university": university, "citizen": citizen, "other": other_citizen, "admin": admin, "recycler": recycler, "pet": pet, "aluminum": aluminum, "point": point, "compartment": compartment, "aluminum_compartment": aluminum_compartment}


@pytest.fixture()
def auth_headers():
    def headers(user: User):
        return {"Authorization": f"Bearer {create_access_token(user.id)}"}

    return headers

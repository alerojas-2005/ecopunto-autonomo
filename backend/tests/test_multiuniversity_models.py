from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models import Collection, Compartment, Deposit, EcoPoint, Material, PointTransaction, TransactionType, University, User, UserRole
from app.schemas.api import CollectionCreate, DepositCreate
from app.services.collections import register_collection
from app.services.deposits import register_deposit


def test_university_slug_is_unique(db_session):
    db_session.add_all([
        University(name="Primera", slug="universidad-a", city="Bogota", campus_name="Sede A"),
        University(name="Segunda", slug="universidad-a", city="Bogota", campus_name="Sede B"),
    ])
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_role_requires_university_except_platform_admin(db_session):
    for role in (UserRole.CITIZEN, UserRole.RECYCLER, UserRole.UNIVERSITY_ADMIN):
        db_session.add(User(
            email=f"{role.value.lower()}-no-university@example.test", full_name="Institutional",
            password_hash="hash", role=role,
        ))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    admin = User(
        email="admin-no-university@example.test", full_name="Admin",
        password_hash="hash", role=UserRole.ADMIN,
    )
    db_session.add(admin)
    db_session.commit()
    assert admin.university_id is None


def test_ecopoint_code_is_unique_per_university(db_session):
    first = University(name="First", slug="first", city="Bogota", campus_name="A")
    second = University(name="Second", slug="second", city="Bogota", campus_name="B")
    db_session.add_all([first, second])
    db_session.flush()
    db_session.add_all([
        EcoPoint(code="ECO-1", name="A1", address="A", university=first),
        EcoPoint(code="ECO-1", name="B1", address="B", university=second),
    ])
    db_session.commit()
    db_session.add(EcoPoint(code="ECO-1", name="A2", address="A", university=first))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def _create_other_university_point(db_session, demo, code="TEST-02"):
    university = University(
        name="Other university", slug=f"other-{code.lower()}", city="Bogota", campus_name="Campus B"
    )
    db_session.add(university)
    db_session.flush()
    material = db_session.query(Material).filter_by(name="PET").one()
    point = EcoPoint(code=code, name="Other EcoPoint", address="B", university=university)
    db_session.add(point)
    db_session.flush()
    compartment = Compartment(
        ecopoint=point, material=material, label="PET B",
        capacity_kg=Decimal("10.000"), current_kg=Decimal("5.000"),
    )
    db_session.add(compartment)
    db_session.commit()
    return university, point, compartment, material


def test_domain_validation_and_sqlite_triggers_reject_cross_university_inserts(client, db_session, demo):
    _, point, compartment, material = _create_other_university_point(db_session, demo)
    with pytest.raises(HTTPException) as deposit_error:
        register_deposit(db_session, demo["citizen"], DepositCreate(
            ecopoint_id=point.id, compartment_id=compartment.id,
            material_id=material.id, weight_g=100,
        ))
    assert deposit_error.value.status_code == 404

    with pytest.raises(IntegrityError, match="deposit university or resource mismatch"):
        db_session.add(Deposit(
            citizen_id=demo["citizen"].id, ecopoint_id=point.id,
            compartment_id=compartment.id, material_id=material.id,
            weight_g=100, factor_applied=Decimal("0.25"), points_awarded=Decimal("25.0000"),
        ))
        db_session.flush()
    db_session.rollback()

    with pytest.raises(HTTPException) as collection_error:
        register_collection(db_session, demo["recycler"], CollectionCreate(
            ecopoint_id=point.id, compartment_id=compartment.id, weight_kg=Decimal("1.000"),
        ))
    assert collection_error.value.status_code == 404

    with pytest.raises(IntegrityError, match="collection university or resource mismatch"):
        db_session.add(Collection(
            ecopoint_id=point.id, compartment_id=compartment.id,
            recycler_id=demo["recycler"].id, weight_kg=Decimal("1.000"),
        ))
        db_session.flush()
    db_session.rollback()

    valid_deposit = Deposit(
        citizen_id=demo["citizen"].id, ecopoint_id=demo["point"].id,
        compartment_id=demo["compartment"].id, material_id=material.id,
        weight_g=100, factor_applied=Decimal("0.25"), points_awarded=Decimal("25.0000"),
    )
    db_session.add(valid_deposit)
    db_session.flush()
    with pytest.raises(IntegrityError, match="point transaction user does not own deposit"):
        db_session.add(PointTransaction(
            user_id=demo["other"].id, deposit_id=valid_deposit.id,
            type=TransactionType.EARN, amount=Decimal("25.0000"), description="Invalid owner",
        ))
        db_session.flush()
    db_session.rollback()


def test_sqlite_triggers_reject_cross_university_updates(client, db_session, demo):
    other_university, other_point, _, material = _create_other_university_point(
        db_session, demo, code="TEST-03"
    )
    deposit = Deposit(
        citizen_id=demo["citizen"].id, ecopoint_id=demo["point"].id,
        compartment_id=demo["compartment"].id, material_id=material.id,
        weight_g=100, factor_applied=Decimal("0.25"), points_awarded=Decimal("25.0000"),
    )
    collection = Collection(
        ecopoint_id=demo["point"].id, compartment_id=demo["compartment"].id,
        recycler_id=demo["recycler"].id, weight_kg=Decimal("1.000"),
    )
    db_session.add_all([deposit, collection])
    db_session.flush()
    transaction = PointTransaction(
        user_id=demo["citizen"].id, deposit_id=deposit.id,
        type=TransactionType.EARN, amount=Decimal("25.0000"), description="Deposit",
    )
    db_session.add(transaction)
    db_session.commit()

    deposit = db_session.get(Deposit, deposit.id)
    deposit.ecopoint_id = other_point.id
    with pytest.raises(IntegrityError, match="deposit university or resource mismatch"):
        db_session.flush()
    db_session.rollback()

    collection = db_session.get(Collection, collection.id)
    collection.ecopoint_id = other_point.id
    with pytest.raises(IntegrityError, match="collection university or resource mismatch"):
        db_session.flush()
    db_session.rollback()

    transaction = db_session.get(PointTransaction, transaction.id)
    transaction.user_id = demo["other"].id
    with pytest.raises(IntegrityError, match="point transaction user does not own deposit"):
        db_session.flush()
    db_session.rollback()

    deposit = db_session.get(Deposit, deposit.id)
    deposit.citizen_id = demo["other"].id
    with pytest.raises(IntegrityError, match="cannot change deposit owner while transactions reference it"):
        db_session.flush()
    db_session.rollback()

    citizen = db_session.get(User, demo["citizen"].id)
    citizen.university_id = other_university.id
    with pytest.raises(IntegrityError, match="cannot reassign user with operational history"):
        db_session.flush()
    db_session.rollback()

    citizen = db_session.get(User, demo["citizen"].id)
    citizen.role = UserRole.RECYCLER
    with pytest.raises(IntegrityError, match="cannot reassign user with operational history"):
        db_session.flush()
    db_session.rollback()

    point = db_session.get(EcoPoint, demo["point"].id)
    point.university_id = other_university.id
    with pytest.raises(IntegrityError, match="cannot reassign ecopoint with operational history"):
        db_session.flush()
    db_session.rollback()

    compartment = db_session.get(Compartment, demo["compartment"].id)
    compartment.ecopoint_id = other_point.id
    with pytest.raises(IntegrityError, match="cannot reassign compartment with operational history"):
        db_session.flush()
    db_session.rollback()

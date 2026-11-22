from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models import (
    Alert, AlertStatus, AlertType, Collection, Compartment, Deposit, EcoPoint,
    Material, PointTransaction, TransactionType, University, User, UserRole,
)
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


def test_role_university_requirements_match_actor_scope(db_session):
    assert {role.value for role in UserRole} == {"ADMIN", "RECYCLER", "CITIZEN"}
    citizen = User(
        email="citizen-no-university@example.test", full_name="Citizen",
        password_hash="hash", role=UserRole.CITIZEN,
    )
    db_session.add(citizen)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    recycler = User(
        email="recycler-no-university@example.test", full_name="Independent recycler",
        password_hash="hash", role=UserRole.RECYCLER,
    )
    db_session.add(recycler)
    db_session.commit()
    assert recycler.university_id is None

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
            recycler_id=demo["recycler"].id, material_id=compartment.material_id,
            weight_kg=Decimal("1.000"),
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
    other_university, other_point, other_compartment, material = _create_other_university_point(
        db_session, demo, code="TEST-03"
    )
    deposit = Deposit(
        citizen_id=demo["citizen"].id, ecopoint_id=demo["point"].id,
        compartment_id=demo["compartment"].id, material_id=material.id,
        weight_g=100, factor_applied=Decimal("0.25"), points_awarded=Decimal("25.0000"),
    )
    collection = Collection(
        ecopoint_id=demo["point"].id, compartment_id=demo["compartment"].id,
        recycler_id=demo["recycler"].id, material_id=demo["compartment"].material_id,
        weight_kg=Decimal("1.000"),
    )
    db_session.add_all([deposit, collection])
    db_session.flush()
    transaction = PointTransaction(
        user_id=demo["citizen"].id, deposit_id=deposit.id,
        type=TransactionType.EARN, amount=Decimal("25.0000"), description="Deposit",
    )
    db_session.add(transaction)
    db_session.commit()

    cross_university_collection = Collection(
        ecopoint_id=other_point.id, compartment_id=other_compartment.id,
        recycler_id=demo["recycler"].id, material_id=other_compartment.material_id,
        weight_kg=Decimal("1.000"),
    )
    db_session.add(cross_university_collection)
    with pytest.raises(IntegrityError, match="collection university or resource mismatch"):
        db_session.flush()
    db_session.rollback()

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


def _add_user(db_session, role, university, email):
    user = User(
        email=email, full_name=f"Test {role.value}", password_hash="test-only-hash",
        role=role, university=university,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _add_alert(db_session, compartment, message):
    alert = Alert(
        compartment=compartment, type=AlertType.FILL_THRESHOLD,
        status=AlertStatus.ACTIVE, message=message,
    )
    db_session.add(alert)
    db_session.commit()
    return alert


def _add_collection(db_session, user, point, compartment):
    collection = Collection(
        ecopoint=point, compartment=compartment, recycler=user,
        material_id=compartment.material_id,
        weight_kg=Decimal("1.000"), notes="Scope test",
    )
    db_session.add(collection)
    db_session.commit()
    return collection


def test_recycler_is_scoped_to_own_university_for_catalog_alerts_and_collections(
    client, db_session, demo, auth_headers
):
    _, other_point, other_compartment, _ = _create_other_university_point(db_session, demo)
    other_alert = _add_alert(db_session, other_compartment, "Foreign alert")
    own_alert = _add_alert(db_session, demo["compartment"], "Own alert")
    headers = auth_headers(demo["recycler"])

    point_list = client.get("/api/v1/ecopoints", headers=headers)
    assert point_list.status_code == 200
    assert [item["id"] for item in point_list.json()] == [str(demo["point"].id)]
    assert client.get(f"/api/v1/ecopoints/{other_point.id}", headers=headers).status_code == 404
    assert client.get(
        f"/api/v1/ecopoints/{other_point.id}/compartments", headers=headers
    ).status_code == 404
    own_compartments = client.get(
        f"/api/v1/ecopoints/{demo['point'].id}/compartments", headers=headers
    )
    assert own_compartments.status_code == 200

    alerts = client.get("/api/v1/alerts", headers=headers)
    assert alerts.status_code == 200
    assert {item["id"] for item in alerts.json()} == {str(own_alert.id)}
    assert client.patch(
        f"/api/v1/alerts/{other_alert.id}/resolve", headers=headers, json={}
    ).status_code == 404
    assert client.patch(
        f"/api/v1/alerts/{own_alert.id}/resolve", headers=headers, json={}
    ).status_code == 200

    own_collection = client.post("/api/v1/collections", headers=headers, json={
        "ecopoint_id": str(demo["point"].id),
        "compartment_id": str(demo["compartment"].id),
        "weight_kg": "1.000",
    })
    assert own_collection.status_code == 201, own_collection.text
    foreign_collection = client.post("/api/v1/collections", headers=headers, json={
        "ecopoint_id": str(other_point.id),
        "compartment_id": str(other_compartment.id),
        "weight_kg": "1.000",
    })
    assert foreign_collection.status_code == 404
    own_collections = client.get("/api/v1/collections", headers=headers)
    assert own_collections.status_code == 200
    assert {item["id"] for item in own_collections.json()} == {own_collection.json()["id"]}
    assert client.get(
        f"/api/v1/collections/{own_collection.json()['id']}", headers=headers
    ).status_code == 200


def test_admin_keeps_global_access_and_citizen_cannot_use_staff_operations(
    client, db_session, demo, auth_headers
):
    _, other_point, other_compartment, material = _create_other_university_point(db_session, demo)
    other_alert = _add_alert(db_session, other_compartment, "Global alert")
    foreign_recycler = _add_user(
        db_session, UserRole.RECYCLER, other_point.university, "global-recycler@example.test"
    )
    foreign_collection = _add_collection(db_session, foreign_recycler, other_point, other_compartment)
    foreign_citizen = _add_user(
        db_session, UserRole.CITIZEN, other_point.university, "global-citizen@example.test"
    )
    foreign_deposit = Deposit(
        citizen_id=foreign_citizen.id, ecopoint_id=other_point.id,
        compartment_id=other_compartment.id, material_id=material.id,
        weight_g=100, factor_applied=Decimal("0.25"), points_awarded=Decimal("25.0000"),
    )
    db_session.add(foreign_deposit)
    db_session.commit()

    admin_headers = auth_headers(demo["admin"])
    points = client.get("/api/v1/ecopoints", headers=admin_headers)
    assert points.status_code == 200
    assert str(other_point.id) in {item["id"] for item in points.json()}
    assert client.get(f"/api/v1/ecopoints/{other_point.id}", headers=admin_headers).status_code == 200
    assert client.get(
        f"/api/v1/ecopoints/{other_point.id}/compartments", headers=admin_headers
    ).status_code == 200
    assert any(item["id"] == str(other_alert.id) for item in client.get(
        "/api/v1/alerts", headers=admin_headers
    ).json())
    assert client.patch(
        f"/api/v1/alerts/{other_alert.id}/resolve", headers=admin_headers, json={}
    ).status_code == 200
    assert client.get("/api/v1/collections", headers=admin_headers).status_code == 200
    assert client.get(
        f"/api/v1/collections/{foreign_collection.id}", headers=admin_headers
    ).status_code == 200
    assert client.get(f"/api/v1/deposits/{foreign_deposit.id}", headers=admin_headers).status_code == 200
    created_point = client.post("/api/v1/ecopoints", headers=admin_headers, json={
        "university_id": str(other_point.university_id), "code": "ADMIN-NEW",
        "name": "Global Admin Point", "address": "Campus",
    })
    assert created_point.status_code == 201

    citizen_headers = auth_headers(demo["citizen"])
    assert client.get(f"/api/v1/ecopoints/{other_point.id}", headers=citizen_headers).status_code == 404
    assert client.get("/api/v1/alerts", headers=citizen_headers).status_code == 403
    assert client.get("/api/v1/collections", headers=citizen_headers).status_code == 403
    assert client.post("/api/v1/collections", headers=citizen_headers, json={
        "ecopoint_id": str(demo["point"].id),
        "compartment_id": str(demo["compartment"].id), "weight_kg": "1.000",
    }).status_code == 403
    assert client.post("/api/v1/deposits", headers=auth_headers(demo["recycler"]), json={
        "ecopoint_id": str(demo["point"].id),
        "compartment_id": str(demo["compartment"].id),
        "material_id": str(demo["pet"].id), "weight_g": 10,
    }).status_code == 403
    assert client.get(
        f"/api/v1/deposits/{foreign_deposit.id}", headers=citizen_headers
    ).status_code == 404
    assert client.post("/api/v1/users", headers=citizen_headers, json={
        "email": "citizen-admin-attempt@example.com", "full_name": "No Admin",
        "password": "A-long-test-password-123", "role": "ADMIN",
    }).status_code == 403
    assert client.post("/api/v1/materials", headers=citizen_headers, json={
        "name": "Forbidden", "points_per_gram": "0.1",
    }).status_code == 403


def _add_deposit(db_session, citizen, point, compartment, material, created_at):
    deposit = Deposit(
        citizen=citizen, ecopoint=point, compartment=compartment, material=material,
        weight_g=100, factor_applied=material.points_per_gram,
        points_awarded=Decimal("25.0000"), created_at=created_at,
    )
    db_session.add(deposit)
    db_session.commit()
    return deposit


def test_deposit_list_filters_and_pagination_cannot_escape_tenant_scope(
    client, db_session, demo, auth_headers
):
    other_university, other_point, other_compartment, material = _create_other_university_point(db_session, demo)
    other_citizen = _add_user(
        db_session, UserRole.CITIZEN, other_university, "deposit-foreign-citizen@example.test"
    )
    first = _add_deposit(
        db_session, demo["citizen"], demo["point"], demo["compartment"], demo["pet"],
        datetime(2025, 1, 2, tzinfo=UTC),
    )
    second = _add_deposit(
        db_session, demo["other"], demo["point"], demo["aluminum_compartment"], demo["aluminum"],
        datetime(2025, 1, 3, tzinfo=UTC),
    )
    foreign = _add_deposit(
        db_session, other_citizen, other_point, other_compartment, material,
        datetime(2025, 1, 4, tzinfo=UTC),
    )

    admin_headers = auth_headers(demo["admin"])
    all_deposits = client.get("/api/v1/deposits", headers=admin_headers)
    assert all_deposits.status_code == 200
    assert {item["id"] for item in all_deposits.json()} == {
        str(first.id), str(second.id), str(foreign.id),
    }
    assert all("password_hash" not in item and "password" not in item for item in all_deposits.json())
    filtered = client.get(
        f"/api/v1/deposits?university_id={other_university.id}&user_id={other_citizen.id}"
        f"&material_id={material.id}&from_date=2025-01-03T00:00:00Z&to_date=2025-01-05T00:00:00Z",
        headers=admin_headers,
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [str(foreign.id)]
    page = client.get("/api/v1/deposits?limit=1&offset=1", headers=admin_headers)
    assert page.status_code == 200 and len(page.json()) == 1

    citizen_headers = auth_headers(demo["citizen"])
    own_deposits = client.get("/api/v1/deposits", headers=citizen_headers)
    assert [item["id"] for item in own_deposits.json()] == [str(first.id)]
    assert client.get(
        f"/api/v1/deposits?user_id={other_citizen.id}", headers=citizen_headers
    ).status_code == 404
    assert client.get(
        f"/api/v1/deposits/{foreign.id}", headers=citizen_headers
    ).status_code == 404
    assert client.get("/api/v1/deposits", headers=auth_headers(demo["recycler"])).status_code == 403

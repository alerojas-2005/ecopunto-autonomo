
from decimal import Decimal

from sqlalchemy import func, select

from app.core.security import verify_password
from app.models import University, User


def test_register_login_and_current_user(client, db_session, demo):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "full_name": "Nueva Ciudadana",
            "password": "StrongPassword123!",
            "university_id": str(demo["university"].id),
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "CITIZEN"
    citizen = db_session.scalar(select(User).where(User.email == "new@example.com"))
    assert citizen is not None
    assert citizen.university_id == demo["university"].id
    assert verify_password("StrongPassword123!", citizen.password_hash)
    assert citizen.password_hash != "StrongPassword123!"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "new@example.com", "password": "StrongPassword123!"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    me = client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"


def test_registration_rejects_unknown_university_without_partial_user(client, db_session):
    response = client.post("/api/v1/auth/register", json={
        "email": "missing@example.com", "full_name": "Missing University",
        "password": "StrongPassword123!",
        "university_id": "00000000-0000-0000-0000-000000000000",
    })
    assert response.status_code == 404
    assert db_session.scalar(select(func.count()).select_from(User).where(User.email == "missing@example.com")) == 0


def test_registration_rejects_university_without_public_registration(client, db_session):
    university = University(name="Closed", slug="closed", city="Bogota", campus_name="Main", active=True, public_registration_enabled=False)
    db_session.add(university)
    db_session.commit()
    response = client.post("/api/v1/auth/register", json={
        "email": "closed@example.com", "full_name": "Closed University",
        "password": "StrongPassword123!", "university_id": str(university.id),
    })
    assert response.status_code == 422
    assert db_session.scalar(select(func.count()).select_from(User).where(User.email == "closed@example.com")) == 0


def test_registration_rejects_duplicate_email(client, db_session, demo):
    demo["citizen"].email = "citizen@example.com"
    db_session.commit()
    response = client.post("/api/v1/auth/register", json={
        "email": "CITIZEN@EXAMPLE.COM", "full_name": "Duplicate",
        "password": "StrongPassword123!", "university_id": str(demo["university"].id),
    })
    assert response.status_code == 409


def test_registration_rejects_administrative_role_field(client, db_session, demo):
    response = client.post("/api/v1/auth/register", json={
        "email": "forged@example.com", "full_name": "No Privileges",
        "password": "StrongPassword123!", "university_id": str(demo["university"].id),
        "role": "ADMIN",
    })
    assert response.status_code == 422
    assert db_session.scalar(select(func.count()).select_from(User).where(User.email == "forged@example.com")) == 0


def test_registration_options_return_only_active_enabled_universities(client, db_session, demo):
    disabled = University(name="Disabled", slug="disabled", city="Bogota", campus_name="Main", active=True, public_registration_enabled=False)
    inactive = University(name="Inactive", slug="inactive", city="Bogota", campus_name="Main", active=False, public_registration_enabled=True)
    db_session.add_all([disabled, inactive])
    db_session.commit()
    response = client.get("/api/v1/universities/registration-options")
    assert response.status_code == 200
    assert response.json() == [{"id": str(demo["university"].id), "name": demo["university"].name}]


def test_authentication_and_role_permissions(client, db_session, demo, auth_headers):
    assert client.get("/api/v1/users/me").status_code == 401

    citizen_material = client.post(
        "/api/v1/materials",
        json={"name": "Vidrio", "points_per_gram": "0.1"},
        headers=auth_headers(demo["citizen"]),
    )
    assert citizen_material.status_code == 403

    created = client.post(
        "/api/v1/materials",
        json={"name": "Vidrio", "points_per_gram": "0.1"},
        headers=auth_headers(demo["admin"]),
    )
    assert created.status_code == 201
    assert created.json()["name"] == "Vidrio"

    recycler = client.post(
        "/api/v1/users",
        json={
            "email": "new-recycler@gmail.com",
            "full_name": "Nuevo Reciclador",
            "password": "StrongPassword123!",
            "role": "RECYCLER",
        },
        headers=auth_headers(demo["admin"]),
    )

    assert recycler.status_code == 422
    assert "universidad" in recycler.json()["detail"].lower()
    assert db_session.scalar(select(func.count()).select_from(User).where(User.email == "new-recycler@gmail.com")) == 0

    recycler = client.post(
        "/api/v1/users",
        json={
            "email": "new-recycler@gmail.com",
            "full_name": "Nuevo Reciclador",
            "password": "StrongPassword123!",
            "role": "RECYCLER",
            "university_id": str(demo["university"].id),
        },
        headers=auth_headers(demo["admin"]),
    )
    assert recycler.status_code == 201
    assert recycler.json()["role"] == "RECYCLER"
    assert recycler.json()["id"]


def test_create_institutional_user_rejects_invalid_university_without_partial_row(
    client, db_session, demo, auth_headers
):
    response = client.post(
        "/api/v1/users",
        json={
            "email": "invalid-university@example.com",
            "full_name": "Usuario Sin Universidad Válida",
            "password": "StrongPassword123!",
            "role": "CITIZEN",
            "university_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=auth_headers(demo["admin"]),
    )

    assert response.status_code == 404, response.text
    assert db_session.scalar(
        select(func.count()).select_from(User).where(User.email == "invalid-university@example.com")
    ) == 0


def test_deposit_awards_points_updates_compartment_and_alert(
    client, demo, auth_headers
):
    response = client.post(
        "/api/v1/deposits",
        headers=auth_headers(demo["citizen"]),
        json={
            "ecopoint_id": str(demo["point"].id),
            "compartment_id": str(demo["compartment"].id),
            "material_id": str(demo["pet"].id),
            "weight_g": 100,
        },
    )

    assert response.status_code == 201, response.text
    assert Decimal(response.json()["points_awarded"]) == Decimal("25.0000")

    balance = client.get(
        "/api/v1/points/balance",
        headers=auth_headers(demo["citizen"]),
    )
    assert Decimal(balance.json()["balance"]) == Decimal("25.0000")

    txs = client.get(
        "/api/v1/points/transactions",
        headers=auth_headers(demo["citizen"]),
    )
    assert len(txs.json()) == 1
    assert txs.json()[0]["type"] == "EARN"

    compartments = client.get(
        f"/api/v1/ecopoints/{demo['point'].id}/compartments",
        headers=auth_headers(demo["citizen"]),
    )
    pet_compartment = next(
        item
        for item in compartments.json()
        if item["id"] == str(demo["compartment"].id)
    )
    assert Decimal(pet_compartment["current_kg"]) == Decimal("19.100")

    alerts = client.get(
        "/api/v1/alerts",
        headers=auth_headers(demo["admin"]),
    )
    assert alerts.status_code == 200
    assert len(alerts.json()) == 1
    assert alerts.json()[0]["status"] == "ACTIVE"

    repeated = client.post(
        "/api/v1/deposits",
        headers=auth_headers(demo["other"]),
        json={
            "ecopoint_id": str(demo["point"].id),
            "compartment_id": str(demo["compartment"].id),
            "material_id": str(demo["pet"].id),
            "weight_g": 100,
        },
    )
    assert repeated.status_code == 201

    assert len(
        client.get(
            "/api/v1/alerts",
            headers=auth_headers(demo["admin"]),
        ).json()
    ) == 1


def test_invalid_and_private_deposits(client, demo, auth_headers):
    headers = auth_headers(demo["citizen"])

    mismatch = client.post(
        "/api/v1/deposits",
        headers=headers,
        json={
            "ecopoint_id": str(demo["point"].id),
            "compartment_id": str(demo["compartment"].id),
            "material_id": str(demo["aluminum"].id),
            "weight_g": 100,
        },
    )
    assert mismatch.status_code == 400

    created = client.post(
        "/api/v1/deposits",
        headers=headers,
        json={
            "ecopoint_id": str(demo["point"].id),
            "compartment_id": str(demo["aluminum_compartment"].id),
            "material_id": str(demo["aluminum"].id),
            "weight_g": 100,
        },
    )
    assert created.status_code == 201
    assert Decimal(created.json()["points_awarded"]) == Decimal("50.0000")

    private = client.get(
        f"/api/v1/deposits/{created.json()['id']}",
        headers=auth_headers(demo["other"]),
    )
    assert private.status_code == 404

    invalid_weight = client.post(
        "/api/v1/deposits",
        headers=headers,
        json={
            "ecopoint_id": str(demo["point"].id),
            "compartment_id": str(demo["aluminum_compartment"].id),
            "material_id": str(demo["aluminum"].id),
            "weight_g": 0,
        },
    )
    assert invalid_weight.status_code == 422

    over_capacity = client.post(
        "/api/v1/deposits",
        headers=headers,
        json={
            "ecopoint_id": str(demo["point"].id),
            "compartment_id": str(demo["compartment"].id),
            "material_id": str(demo["pet"].id),
            "weight_g": 2000,
        },
    )
    assert over_capacity.status_code == 409


def test_recycler_collection_resolves_alert(client, demo, auth_headers):
    deposit = client.post(
        "/api/v1/deposits",
        headers=auth_headers(demo["citizen"]),
        json={
            "ecopoint_id": str(demo["point"].id),
            "compartment_id": str(demo["compartment"].id),
            "material_id": str(demo["pet"].id),
            "weight_g": 100,
        },
    )
    assert deposit.status_code == 201

    headers = auth_headers(demo["recycler"])

    response = client.post(
        "/api/v1/collections",
        headers=headers,
        json={
            "ecopoint_id": str(demo["point"].id),
            "compartment_id": str(demo["compartment"].id),
            "weight_kg": "4.000",
            "notes": "Retiro de prueba",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "COMPLETED"

    alerts = client.get(
        "/api/v1/alerts",
        headers=auth_headers(demo["admin"]),
    )
    assert alerts.json()[0]["status"] == "RESOLVED"

    own = client.get("/api/v1/collections", headers=headers)
    assert len(own.json()) == 1

    assert (
        client.get(
            "/api/v1/collections",
            headers=auth_headers(demo["citizen"]),
        ).status_code
        == 403
    )

    forbidden = client.post(
        "/api/v1/collections",
        headers=auth_headers(demo["citizen"]),
        json={
            "ecopoint_id": str(demo["point"].id),
            "compartment_id": str(demo["compartment"].id),
            "weight_kg": "1.000",
        },
    )
    assert forbidden.status_code == 403

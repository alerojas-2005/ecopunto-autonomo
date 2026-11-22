
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from app.core.security import verify_password
from app.models import University, User, UserRole


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


def test_university_management_is_global_only_for_admin(client, db_session, demo, auth_headers):
    other = University(
        name="Otra Universidad", slug="otra-universidad", city="Bogota",
        campus_name="Sede alterna", active=False, public_registration_enabled=False,
    )
    db_session.add(other)
    db_session.commit()
    admin_headers = auth_headers(demo["admin"])
    all_universities = client.get("/api/v1/universities", headers=admin_headers)
    assert all_universities.status_code == 200
    assert {item["id"] for item in all_universities.json()} == {
        str(demo["university"].id), str(other.id),
    }
    active_universities = client.get("/api/v1/universities?active=true", headers=admin_headers)
    assert {item["id"] for item in active_universities.json()} == {str(demo["university"].id)}
    assert client.patch(
        f"/api/v1/universities/{other.id}", headers=admin_headers,
        json={"active": True, "public_registration_enabled": True},
    ).status_code == 200

    for user in (demo["citizen"], demo["recycler"]):
        headers = auth_headers(user)
        own = client.get("/api/v1/universities", headers=headers)
        assert own.status_code == 200
        assert [item["id"] for item in own.json()] == [str(demo["university"].id)]
        assert client.get(f"/api/v1/universities/{other.id}", headers=headers).status_code == 404
        assert client.patch(
            f"/api/v1/universities/{demo['university'].id}", headers=headers,
            json={"name": "Attempted edit"},
        ).status_code == 403


def test_admin_user_management_is_global_and_redacted(client, db_session, demo, auth_headers):
    other_university = University(
        name="Otra Universidad", slug="user-otra-universidad", city="Bogota",
        campus_name="Sede principal", active=True,
    )
    db_session.add(other_university)
    db_session.flush()
    foreign_user = User(
        email="foreign-user@example.test", full_name="Foreign User",
        password_hash="sensitive-test-hash", role=UserRole.CITIZEN,
        university=other_university,
    )
    db_session.add(foreign_user)
    db_session.commit()

    admin_headers = auth_headers(demo["admin"])
    all_users = client.get("/api/v1/users", headers=admin_headers)
    assert all_users.status_code == 200
    assert {item["id"] for item in all_users.json()} == {
        str(demo["citizen"].id), str(demo["other"].id), str(demo["recycler"].id),
        str(demo["admin"].id), str(foreign_user.id),
    }
    assert all("password_hash" not in item and "password" not in item for item in all_users.json())
    assert client.get(f"/api/v1/users/{foreign_user.id}", headers=admin_headers).status_code == 200

    created = client.post("/api/v1/users", headers=admin_headers, json={
        "email": "admin-created@example.com", "full_name": "Platform User",
        "password": "A-long-test-password-123", "role": "CITIZEN",
        "university_id": str(demo["university"].id),
    })
    assert created.status_code == 201, created.text
    assert created.json()["university_id"] == str(demo["university"].id)
    assert "password_hash" not in created.json() and "password" not in created.json()
    assert client.post("/api/v1/users", headers=admin_headers, json={
        "email": "admin-recycler@example.com", "full_name": "New Recycler",
        "password": "A-long-test-password-123", "role": "RECYCLER",
        "university_id": str(other_university.id),
    }).status_code == 201
    assert client.post("/api/v1/users", headers=admin_headers, json={
        "email": "admin-legacy-role@example.com", "full_name": "Invalid Role",
        "password": "A-long-test-password-123", "role": "UNIVERSITY_ADMIN",
        "university_id": str(other_university.id),
    }).status_code == 422
    assert client.patch(
        f"/api/v1/users/{foreign_user.id}", headers=admin_headers,
        json={"role": "UNIVERSITY_ADMIN"},
    ).status_code == 422

    admin_update = client.patch(
        f"/api/v1/users/{foreign_user.id}", headers=admin_headers,
        json={"full_name": "Admin Updated"},
    )
    assert admin_update.status_code == 200
    assert "password_hash" not in admin_update.json() and "password" not in admin_update.json()
    global_role_update = client.patch(
        f"/api/v1/users/{foreign_user.id}", headers=admin_headers,
        json={"role": "ADMIN"},
    )
    assert global_role_update.status_code == 200
    assert global_role_update.json()["role"] == "ADMIN"
    assert global_role_update.json()["university_id"] is None
    assert "password_hash" not in global_role_update.json()
    for non_admin in (demo["citizen"], demo["recycler"]):
        headers = auth_headers(non_admin)
        assert client.get("/api/v1/users", headers=headers).status_code == 403
        assert client.get(f"/api/v1/users/{foreign_user.id}", headers=headers).status_code == 403
        assert client.patch(
            f"/api/v1/users/{demo['citizen'].id}", headers=headers,
            json={"full_name": "No Access"},
        ).status_code == 403


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
    assert recycler.json()["university_id"] == str(demo["university"].id)
    assert "password_hash" not in recycler.json() and "password" not in recycler.json()
    listed = client.get("/api/v1/users", headers=auth_headers(demo["admin"]))
    assert any(user["id"] == recycler.json()["id"] for user in listed.json())
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "new-recycler@gmail.com", "password": "StrongPassword123!"},
    )
    assert login_response.status_code == 200
    recycler_me = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
    )
    assert recycler_me.status_code == 200
    assert recycler_me.json()["university_id"] == str(demo["university"].id)
    assert recycler_me.json()["role"] == "RECYCLER"


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


def test_unidentified_deposit_is_stored_without_points(client, demo, auth_headers, db_session):
    from decimal import Decimal
    from sqlalchemy import select
    from app.models import Compartment, Deposit, PointTransaction

    unknown = Compartment(
        ecopoint_id=demo["point"].id, material_id=None, label="No identificados",
        capacity_kg=Decimal("0.300"), current_kg=Decimal("0.000"),
        fill_threshold_pct=80, active=True,
    )
    db_session.add(unknown)
    db_session.commit()
    unknown_id = unknown.id

    response = client.post(
        "/api/v1/deposits", headers=auth_headers(demo["citizen"]), json={
            "ecopoint_id": str(demo["point"].id), "compartment_id": str(unknown_id), "weight_g": 250,
        },
    )
    assert response.status_code == 201
    assert response.json()["material_id"] is None
    assert Decimal(response.json()["factor_applied"]) == Decimal("0.0000")
    assert Decimal(response.json()["points_awarded"]) == Decimal("0.0000")
    deposit_id = UUID(response.json()["id"])
    deposit = db_session.get(Deposit, deposit_id)
    assert deposit.material_id is None and deposit.points_awarded == Decimal("0.0000")
    assert db_session.scalar(select(PointTransaction).where(PointTransaction.deposit_id == deposit_id)) is None
    db_session.expire_all()
    assert db_session.get(Compartment, unknown_id).current_kg == Decimal("0.250")
    compartment_response = client.get(
        f"/api/v1/ecopoints/{demo['point'].id}/compartments",
        headers=auth_headers(demo["citizen"]),
    )
    unknown_response = next(item for item in compartment_response.json() if item["id"] == str(unknown_id))
    assert Decimal(unknown_response["fill_percentage"]) == Decimal("83.33")
    alerts = client.get("/api/v1/alerts", headers=auth_headers(demo["admin"]))
    assert alerts.status_code == 200
    assert any(item["compartment_id"] == str(unknown_id) for item in alerts.json())


def test_catalog_seed_records_are_available_through_frontend_endpoints(
    client, demo, auth_headers, db_session, monkeypatch
):
    from sqlalchemy.orm import sessionmaker
    from app import seed as seed_module

    monkeypatch.setattr(seed_module, "engine", db_session.get_bind())
    monkeypatch.setattr(
        seed_module, "SessionLocal", sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    )
    seed_module.seed()

    headers = auth_headers(demo["citizen"])
    materials = client.get("/api/v1/materials", headers=headers)
    points = client.get("/api/v1/ecopoints", headers=headers)
    compartments = client.get(
        f"/api/v1/ecopoints/{demo['point'].id}/compartments", headers=headers
    )

    assert materials.status_code == points.status_code == compartments.status_code == 200
    assert len(materials.json()) == 7
    assert any(item["id"] == str(demo["point"].id) for item in points.json())
    assert len(compartments.json()) == 8
    assert sum(item["material_id"] is None for item in compartments.json()) == 1

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

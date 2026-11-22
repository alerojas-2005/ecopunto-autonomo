from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (AssignmentStatus, Compartment, CoverageSector, EcoPoint, Organization,
                        Collection, OrganizationStatus, OrganizationType, RecyclerAssignment,
                        RecyclerLinkType, RecyclerProfile, University, User, UserRole)


def test_independent_recycler_profile_persists_without_university_or_organization(db_session):
    user = User(
        email="independent-profile@example.com",
        full_name="Reciclador independiente",
        password_hash="test-hash",
        role=UserRole.RECYCLER,
        university_id=None,
    )
    db_session.add(user)
    db_session.flush()
    persisted_user_id = user.id

    profile = RecyclerProfile(
        user_id=persisted_user_id,
        organization_id=None,
        link_type=RecyclerLinkType.INDEPENDENT,
    )
    db_session.add(profile)
    db_session.commit()

    stored_profile = db_session.get(RecyclerProfile, persisted_user_id)
    assert stored_profile is not None
    assert stored_profile.user_id == persisted_user_id == user.id
    assert stored_profile.organization_id is None
    assert stored_profile.link_type == RecyclerLinkType.INDEPENDENT
    assert stored_profile.user.university_id is None
    assert db_session.connection().exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1


def test_admin_can_create_organization_and_independent_recycler(client, db_session, demo, auth_headers):
    headers = auth_headers(demo["admin"])
    organization = client.post("/api/v1/recyclers/organizations", headers=headers, json={
        "name": "Cooperativa de prueba", "type": "COOPERATIVE", "city": "Bogotá",
    })
    assert organization.status_code == 201, organization.text
    created = client.post("/api/v1/recyclers", headers=headers, json={
        "email": "independent@example.com", "full_name": "Recicladora Independiente",
        "password": "StrongPassword123!", "organization_id": None,
    })
    assert created.status_code == 201, created.text
    assert created.json()["university_id"] is None
    assert created.json()["organization_id"] is None
    user = db_session.query(User).filter_by(email="independent@example.com").one()
    assert user.role == UserRole.RECYCLER
    assert user.password_hash != "StrongPassword123!"
    login = client.post("/api/v1/auth/login", json={"email":"independent@example.com","password":"StrongPassword123!"})
    assert login.status_code == 200
    assert client.get("/api/v1/recyclers/me/dashboard", headers={"Authorization":f"Bearer {login.json()['access_token']}"}).status_code == 200


def test_linked_recyclers_and_organization_membership(client, db_session, demo, auth_headers):
    headers = auth_headers(demo["admin"])
    org = Organization(name="Asociación", type=OrganizationType.ASSOCIATION, city="Bogotá", status=OrganizationStatus.ACTIVE)
    db_session.add(org); db_session.commit()
    for index in (1, 2):
        response = client.post("/api/v1/recyclers", headers=headers, json={
            "email": f"member{index}@example.com", "full_name": f"Miembro {index}",
            "password": "StrongPassword123!", "organization_id": str(org.id),
        })
        assert response.status_code == 201, response.text
        assert response.json()["link_type"] == "ORGANIZATION"
        assert response.json()["organization_id"] == str(org.id)
    inactive_org = Organization(name="Pendiente", type=OrganizationType.ASSOCIATION, city="Bogotá")
    db_session.add(inactive_org)
    db_session.commit()
    inactive_response = client.post("/api/v1/recyclers", headers=headers, json={
        "email": "inactive-org@example.com", "full_name": "No autorizado",
        "password": "StrongPassword123!", "organization_id": str(inactive_org.id),
    })
    assert inactive_response.status_code == 422
    missing_response = client.post("/api/v1/recyclers", headers=headers, json={
        "email": "missing-org@example.com", "full_name": "Sin organización real",
        "password": "StrongPassword123!", "organization_id": "00000000-0000-0000-0000-000000000001",
    })
    assert missing_response.status_code == 404
    members = client.get(f"/api/v1/recyclers/organizations/{org.id}/recyclers", headers=headers)
    assert members.status_code == 200
    assert len(members.json()) == 2


def test_organization_coverage_generates_authorizations_and_login(client, db_session, demo, auth_headers):
    headers = auth_headers(demo["admin"])
    org_response = client.post("/api/v1/recyclers/organizations", headers=headers, json={
        "name": "Cobertura activa", "type": "ASSOCIATION", "city": "Bogotá", "status": "ACTIVE",
    })
    sector_response = client.post("/api/v1/recyclers/sectors", headers=headers, json={
        "name": "Sector centro", "locality": "Localidad de prueba", "city": "Bogotá",
    })
    assert org_response.status_code == 201 and sector_response.status_code == 201
    sector_id = sector_response.json()["id"]
    linked = client.put(f"/api/v1/recyclers/sectors/{sector_id}/ecopoints", headers=headers,
                        json={"ecopoint_ids": [str(demo["point"].id)]})
    assert linked.status_code == 200, linked.text
    coverage = client.put(f"/api/v1/recyclers/organizations/{org_response.json()['id']}/coverage",
        headers=headers, json={"sector_ids": [sector_id], "ecopoint_ids": [str(demo["point"].id)]})
    assert coverage.status_code == 200, coverage.text
    created = client.post("/api/v1/recyclers", headers=headers, json={
        "email": "covered@example.com", "full_name": "Reciclador Vinculado",
        "password": "StrongPassword123!", "link_type": "ORGANIZATION",
        "organization_id": org_response.json()["id"],
    })
    assert created.status_code == 201, created.text
    assignments = client.get("/api/v1/recyclers/assignments", headers=auth_headers(
        db_session.query(User).filter_by(email="covered@example.com").one()))
    assert assignments.status_code == 200
    assert any(item["ecopoint_id"] == str(demo["point"].id) for item in assignments.json())
    login = client.post("/api/v1/auth/login", json={"email": "covered@example.com", "password": "StrongPassword123!"})
    assert login.status_code == 200
    recycler_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    accepted = client.post("/api/v1/collections", headers=recycler_headers, json={
        "ecopoint_id": str(demo["point"].id), "compartment_id": str(demo["compartment"].id), "weight_kg": "0.2",
    })
    assert accepted.status_code == 201, accepted.text
    dashboard = client.get("/api/v1/recyclers/me/dashboard", headers=recycler_headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["profile"]["organization_name"] == "Cobertura activa"
    assert dashboard.json()["collection_count"] == 1
    assert dashboard.json()["recovered_weight_kg"] == "0.200"
    second_point = EcoPoint(code="OTHER-01", name="Punto fuera de cobertura", address="Sin sector confirmado", active=True, university=demo["university"])
    second_compartment = Compartment(
        ecopoint=second_point, material=demo["pet"], label="PET otro punto",
        capacity_kg=Decimal("10.000"), current_kg=Decimal("5.000"),
        fill_threshold_pct=80, active=True,
    )
    db_session.add_all([second_point, second_compartment]); db_session.commit()
    recycler_user = db_session.query(User).filter_by(email="covered@example.com").one()
    collection = client.post("/api/v1/collections", headers=auth_headers(recycler_user), json={
        "ecopoint_id": str(second_point.id), "compartment_id": str(demo["compartment"].id), "weight_kg": "0.1",
    })
    assert collection.status_code == 403
    mismatched_compartment = client.post("/api/v1/collections", headers=auth_headers(recycler_user), json={
        "ecopoint_id": str(demo["point"].id), "compartment_id": str(second_compartment.id), "weight_kg": "0.1",
    })
    assert mismatched_compartment.status_code == 404


def test_changing_organization_revokes_old_automatic_grants(client, db_session, demo, auth_headers):
    headers = auth_headers(demo["admin"])
    org_a = Organization(name="Org A", type=OrganizationType.ASSOCIATION, city="Bogotá", status=OrganizationStatus.ACTIVE)
    org_b = Organization(name="Org B", type=OrganizationType.COOPERATIVE, city="Bogotá", status=OrganizationStatus.ACTIVE)
    sector = CoverageSector(locality="Localidad", name="Sector", city="Bogotá", active=True)
    db_session.add_all([org_a,org_b,sector]);db_session.flush()
    org_a.sectors=[sector];sector.ecopoints=[demo["point"]];db_session.commit()
    person = client.post("/api/v1/recyclers", headers=headers, json={"email":"switch@example.com","full_name":"Cambio","password":"StrongPassword123!","link_type":"ORGANIZATION","organization_id":str(org_a.id)})
    assert person.status_code==201,person.text
    person_id=UUID(person.json()["id"])
    token=auth_headers(db_session.get(User, person_id))
    old_rows=client.get("/api/v1/recyclers/assignments",headers=token).json()
    assert any(row["organization_id"]==str(org_a.id) and row["ecopoint_id"]==str(demo["point"].id) and row["status"]=="ACTIVE" and row["origin"]=="AUTOMATIC" for row in old_rows)
    sector_b = CoverageSector(locality="Localidad", name="Sector B", city="Bogotá", active=True)
    db_session.add(sector_b); db_session.flush()
    org_b.sectors = [sector_b]
    sector_b.ecopoints = [demo["point"]]
    db_session.commit()
    changed=client.patch(f"/api/v1/recyclers/{person_id}",headers=headers,json={"organization_id":str(org_b.id)})
    assert changed.status_code==200,changed.text
    assert changed.json()["organization_id"] == str(org_b.id)
    rows=client.get("/api/v1/recyclers/assignments",headers=token).json()
    assert any(row["organization_id"]==str(org_a.id) and row["status"]=="INACTIVE" and row["origin"]=="AUTOMATIC" for row in rows)
    assert not any(row["organization_id"]==str(org_a.id) and row["status"]=="ACTIVE" for row in rows)
    assert any(row["organization_id"]==str(org_b.id) and row["sector_id"]==str(sector_b.id) and row["status"]=="ACTIVE" and row["origin"]=="AUTOMATIC" and row["ecopoint_id"]==str(demo["point"].id) for row in rows)
    assert len([row for row in rows if row["organization_id"]==str(org_a.id)]) == 1


def test_collection_trigger_rejects_compartment_material_mismatch(client, db_session, demo):
    invalid = Collection(
        recycler_id=demo["recycler"].id,
        ecopoint_id=demo["point"].id,
        compartment_id=demo["compartment"].id,
        material_id=demo["aluminum"].id,
        weight_kg=Decimal("0.100"),
    )
    db_session.add(invalid)
    with pytest.raises(IntegrityError, match="collection university or resource mismatch"):
        db_session.commit()
    db_session.rollback()


def test_assignment_duplicate_and_ecopoint_university_validation(client, db_session, demo, auth_headers):
    headers = auth_headers(demo["admin"])
    sector = CoverageSector(locality="Localidad de prueba", name="Sector norte", city="Bogotá", active=True)
    other_university = University(name="Otra", slug="otra-prueba", city="Bogotá", campus_name="Sede")
    db_session.add_all([sector, other_university]); db_session.commit()
    base = {"recycler_id": str(demo["recycler"].id), "sector_id": str(sector.id), "status": "ACTIVE"}
    assert client.post("/api/v1/recyclers/assignments", headers=headers, json=base).status_code == 201
    assert client.post("/api/v1/recyclers/assignments", headers=headers, json=base).status_code == 409
    mismatch = {"recycler_id": str(demo["recycler"].id), "university_id": str(other_university.id),
                "ecopoint_id": str(demo["point"].id), "status": "ACTIVE"}
    assert client.post("/api/v1/recyclers/assignments", headers=headers, json=mismatch).status_code == 422


def test_recycler_collection_requires_active_assignment(client, db_session, demo, auth_headers):
    headers = auth_headers(demo["recycler"])
    assignment = RecyclerAssignment(recycler_id=demo["recycler"].id,
        ecopoint_id=demo["point"].id, university_id=demo["university"].id,
        status=AssignmentStatus.INACTIVE)
    db_session.add(assignment); db_session.commit()
    payload = {"ecopoint_id": str(demo["point"].id), "compartment_id": str(demo["compartment"].id), "weight_kg": "0.5"}
    denied = client.post("/api/v1/collections", headers=headers, json=payload)
    assert denied.status_code == 403
    assignment.status = AssignmentStatus.ACTIVE; db_session.commit()
    allowed = client.post("/api/v1/collections", headers=headers, json=payload)
    assert allowed.status_code == 201, allowed.text
    assert allowed.json()["recycler_id"] == str(demo["recycler"].id)


def test_citizen_cannot_access_recycler_administration(client, demo, auth_headers):
    response = client.get("/api/v1/recyclers/organizations", headers=auth_headers(demo["citizen"]))
    assert response.status_code == 403

"""Create idempotent, non-sensitive demo materials and a demo EcoPunto."""
from decimal import Decimal

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.models import Compartment, EcoPoint, Material
from app import models  # noqa: F401


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        aluminum = db.scalar(select(Material).where(Material.name == "Aluminio"))
        if aluminum is None:
            aluminum = Material(name="Aluminio", description="Latas y envases de aluminio", points_per_gram=Decimal("0.50"))
            db.add(aluminum)
        pet = db.scalar(select(Material).where(Material.name == "PET"))
        if pet is None:
            pet = Material(name="PET", description="Envases plásticos PET", points_per_gram=Decimal("0.25"))
            db.add(pet)
        point = db.scalar(select(EcoPoint).where(EcoPoint.code == "ECO-BOG-001"))
        if point is None:
            point = EcoPoint(code="ECO-BOG-001", name="EcoPunto Parque Central", address="Bogotá, Colombia")
            db.add(point)
        db.flush()
        for material, label in ((aluminum, "Aluminio"), (pet, "PET")):
            compartment = db.scalar(select(Compartment).where(Compartment.ecopoint_id == point.id, Compartment.material_id == material.id))
            if compartment is None:
                db.add(Compartment(ecopoint_id=point.id, material_id=material.id, label=label, capacity_kg=Decimal("25.000"), current_kg=Decimal("0.000"), fill_threshold_pct=80))
        db.commit()
    print("Datos de demostración creados o ya existentes. No se crearon usuarios ni contraseñas.")


if __name__ == "__main__":
    seed()

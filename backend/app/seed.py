"""Initialize global materials and simulated university collection points."""

from decimal import Decimal

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.core.sqlite_integrity import install_sqlite_integrity_triggers
from app.core.sqlite_migrations import upgrade_unidentified_deposits
from app.models import Compartment, EcoPoint, Material, University
from app import models  # noqa: F401


MATERIAL_CATALOG = (
    ("Aluminio", "Latas y envases de aluminio", Decimal("0.50")),
    ("PET", "Envases plasticos PET", Decimal("0.25")),
    ("Otros plásticos", "Otros plásticos reciclables", Decimal("0.20")),
    ("Cartón", "Cartón reciclable", Decimal("0.10")),
    ("Papel", "Papel reciclable", Decimal("0.10")),
    ("Tetra Pak", "Envases Tetra Pak", Decimal("0.08")),
    ("Vidrio", "Envases de vidrio", Decimal("0.05")),
)
UNKNOWN_COMPARTMENT_LABEL = "No identificados"
# 25 kg is the capacity already used by the previous seed configuration.
COMPARTMENT_CAPACITY_KG = Decimal("25.000")
FILL_THRESHOLD_PCT = 80


def seed() -> None:
    upgrade_unidentified_deposits(engine)
    Base.metadata.create_all(bind=engine)
    install_sqlite_integrity_triggers(engine)
    with SessionLocal() as db:
        universities = db.scalars(select(University).order_by(University.slug)).all()
        if not universities:
            raise RuntimeError("No hay universidades cargadas; no se crearon universidades nuevas")

        materials = {material.name: material for material in db.scalars(select(Material)).all()}
        conflicts = [
            name for name, _description, factor in MATERIAL_CATALOG
            if name in materials and Decimal(materials[name].points_per_gram) != factor
        ]
        if conflicts:
            raise RuntimeError(f"Factores existentes distintos a los definidos: {', '.join(conflicts)}")

        for name, description, factor in MATERIAL_CATALOG:
            if name not in materials:
                material = Material(name=name, description=description, points_per_gram=factor, active=True)
                db.add(material)
                materials[name] = material
        db.flush()

        for university in universities:
            points = db.scalars(
                select(EcoPoint).where(EcoPoint.university_id == university.id).order_by(EcoPoint.id)
            ).all()
            if len(points) > 1:
                raise RuntimeError(f"La universidad {university.slug} ya tiene mas de un EcoPunto")
            if points:
                point = points[0]
            else:
                code = f"SIM-{university.id.hex[:12].upper()}"
                point = EcoPoint(
                    university_id=university.id,
                    code=code,
                    name=f"EcoPunto simulado - {university.name}"[:120],
                    address="Instalacion virtual de simulacion academica",
                    active=True,
                )
                db.add(point)
                db.flush()

            existing_bins = db.scalars(select(Compartment).where(
                Compartment.ecopoint_id == point.id,
            )).all()
            allowed_material_ids = {materials[name].id for name, _description, _factor in MATERIAL_CATALOG}
            bin_material_ids = [bin_.material_id for bin_ in existing_bins]
            if any(material_id is not None and material_id not in allowed_material_ids for material_id in bin_material_ids):
                raise RuntimeError(f"El EcoPunto {point.code} tiene compartimentos fuera del catalogo global")
            if len(bin_material_ids) != len(set(bin_material_ids)):
                raise RuntimeError(f"El EcoPunto {point.code} tiene compartimentos duplicados")

            for name, _description, _factor in MATERIAL_CATALOG:
                material = materials[name]
                compartment = db.scalar(select(Compartment).where(
                    Compartment.ecopoint_id == point.id,
                    Compartment.material_id == material.id,
                ))
                if compartment is None:
                    db.add(Compartment(
                        ecopoint_id=point.id,
                        material_id=material.id,
                        label=name,
                        capacity_kg=COMPARTMENT_CAPACITY_KG,
                        current_kg=Decimal("0.000"),
                        fill_threshold_pct=FILL_THRESHOLD_PCT,
                        active=True,
                    ))
            unknown = db.scalars(select(Compartment).where(
                Compartment.ecopoint_id == point.id,
                Compartment.material_id.is_(None),
            )).all()
            if len(unknown) > 1:
                raise RuntimeError(f"El EcoPunto {point.code} tiene compartimentos sin material duplicados")
            if not unknown:
                db.add(Compartment(
                    ecopoint_id=point.id,
                    material_id=None,
                    label=UNKNOWN_COMPARTMENT_LABEL,
                    capacity_kg=COMPARTMENT_CAPACITY_KG,
                    current_kg=Decimal("0.000"),
                    fill_threshold_pct=FILL_THRESHOLD_PCT,
                    active=True,
                ))
        db.commit()
    print("Catalogo inicial y EcoPuntos simulados creados o ya existentes.")


if __name__ == "__main__":
    seed()

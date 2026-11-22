"""Load the SNIES-verified Bogotá university catalog into the current schema."""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.models import University  # noqa: E402
from app import models  # noqa: E402,F401


BOGOTA_UNIVERSITIES = (
    "COLEGIO MAYOR DE NUESTRA SEÑORA DEL ROSARIO",
    "DIRECCION DE EDUCACION POLICIAL",
    "FUNDACION UNIVERSIDAD AUTONOMA DE COLOMBIA -FUAC-",
    "FUNDACION UNIVERSIDAD DE AMERICA",
    "FUNDACION UNIVERSIDAD DE BOGOTA - JORGE TADEO LOZANO",
    "PONTIFICIA UNIVERSIDAD JAVERIANA",
    "UNIVERSIDAD ANTONIO NARIÑO",
    "UNIVERSIDAD CENTRAL",
    "UNIVERSIDAD COOPERATIVA DE COLOMBIA",
    "UNIVERSIDAD DE CIENCIAS APLICADAS Y AMBIENTALES - UDCA",
    "UNIVERSIDAD DE LA SALLE",
    "UNIVERSIDAD DE LOS ANDES",
    "UNIVERSIDAD DISTRITAL-FRANCISCO JOSE DE CALDAS",
    "UNIVERSIDAD EAN",
    "UNIVERSIDAD ECCI",
    "UNIVERSIDAD EL BOSQUE",
    "UNIVERSIDAD ESCUELA COLOMBIANA DE INGENIERIA JULIO GARAVITO",
    "UNIVERSIDAD EXTERNADO DE COLOMBIA",
    "UNIVERSIDAD FUCS",
    "UNIVERSIDAD INCCA DE COLOMBIA",
    "UNIVERSIDAD LA GRAN COLOMBIA",
    "UNIVERSIDAD LIBRE",
    "UNIVERSIDAD MILITAR-NUEVA GRANADA",
    "UNIVERSIDAD NACIONAL ABIERTA Y A DISTANCIA UNAD",
    "UNIVERSIDAD NACIONAL DE COLOMBIA",
    "UNIVERSIDAD PEDAGOGICA NACIONAL",
    "UNIVERSIDAD SANTO TOMAS",
    "UNIVERSIDAD SERGIO ARBOLEDA",
    "UNIVERSIDAD-COLEGIO MAYOR DE CUNDINAMARCA",
    "CORPORACION UNIVERSIDAD PILOTO DE COLOMBIA",
    "UNIVERSIDAD MANUELA BELTRAN-UMB-",
    "UNIVERSIDAD DE SAN BUENAVENTURA",
)


def slug_for(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", normalized.lower())).strip("-")


def load_universities(db: Session) -> int:
    """Insert missing catalog universities by stable slug; preserve existing rows."""
    existing = set(db.scalars(select(University.slug)).all())
    added = 0
    for name in BOGOTA_UNIVERSITIES:
        slug = slug_for(name)
        if slug in existing:
            continue
        db.add(University(
            name=name,
            slug=slug,
            city="Bogotá D.C.",
            campus_name="Bogotá D.C.",
            active=True,
            public_registration_enabled=False,
        ))
        existing.add(slug)
        added += 1
    return added


def main() -> int:
    # Match main.py's schema initialization without invoking the demo seed.
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        try:
            added = load_universities(db)
            db.commit()
        except Exception:
            db.rollback()
            raise
    print(f"Universidades insertadas: {added}; catálogo objetivo: {len(BOGOTA_UNIVERSITIES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Explicitly relax the legacy RECYCLER university constraint on a SQLite copy.

Example: python scripts/migrations/migrate_recycler_module.py --database copy.db --backup copy.pre-recyclers.db
The application never calls this script at startup.
"""
import argparse
import hashlib
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.core.sqlite_migrations import upgrade_recycler_university_optional


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True, help="SQLite database to migrate")
    parser.add_argument("--backup", type=Path, required=True, help="New path for a verified backup; must not exist")
    args = parser.parse_args()
    database = args.database.resolve()
    backup = args.backup.resolve()
    if not database.is_file():
        parser.error("--database debe ser un archivo existente")
    if database == backup or backup.exists():
        parser.error("--backup debe ser una ruta distinta que todavía no exista")
    backup.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as source, sqlite3.connect(backup) as target:
        source.backup(target)
        if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            parser.error("El backup no superó integrity_check")
    before_hash = digest(backup)
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    try:
        changed = upgrade_recycler_university_optional(engine)
        with engine.connect() as connection:
            if connection.exec_driver_sql("PRAGMA integrity_check").scalar_one() != "ok":
                raise RuntimeError("La base migrada no superó integrity_check")
            violations = connection.exec_driver_sql("PRAGMA foreign_key_check").all()
            if violations:
                raise RuntimeError(f"La base migrada tiene referencias inválidas: {violations[:5]}")
    finally:
        engine.dispose()
    if digest(backup) != before_hash:
        raise RuntimeError("El backup cambió durante la migración")
    print(f"Migración {'aplicada' if changed else 'ya aplicada'}; backup verificado SHA-256 {before_hash}")


if __name__ == "__main__":
    main()

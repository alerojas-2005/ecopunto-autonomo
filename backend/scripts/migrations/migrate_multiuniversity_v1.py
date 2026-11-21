"""Version 1 SQLite migration for EcoPunto's multi-university model.

This script is intentionally explicit about its database and backup paths. It
must be rehearsed on a restored copy before it is pointed at a live database.
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

VERSION = "0001_multiuniversity"
LEGACY_UNIVERSITY_ID = UUID("00000000-0000-4000-8000-000000000001")
LEGACY_UNIVERSITY_SLUG = "universidad-legado-pendiente"
EXPECTED_TABLES = {
    "users", "ecopoints", "materials", "compartments", "deposits",
    "point_transactions", "alerts", "collections",
}
USER_COLUMNS = (
    "id", "email", "full_name", "password_hash", "role", "is_active", "created_at",
)
ECOPOINT_COLUMNS = ("id", "code", "name", "address", "active", "created_at")


class MigrationError(RuntimeError):
    pass


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _assert_legacy_schema(connection: sqlite3.Connection) -> None:
    tables = _table_names(connection)
    missing = EXPECTED_TABLES - tables
    if missing:
        raise MigrationError(f"La base no contiene las tablas esperadas: {', '.join(sorted(missing))}")
    if "universities" in tables:
        raise MigrationError("Ya existe universities pero no hay una versión de esta migración registrada")
    if "university_id" in _columns(connection, "users") or "university_id" in _columns(connection, "ecopoints"):
        raise MigrationError("El esquema parece parcialmente migrado; se requiere revisión manual")
    for table, expected in (("users", set(USER_COLUMNS)), ("ecopoints", set(ECOPOINT_COLUMNS))):
        actual = _columns(connection, table)
        if actual != expected:
            raise MigrationError(
                f"Columnas inesperadas en {table}: faltan {sorted(expected - actual)}, "
                f"sobran {sorted(actual - expected)}"
            )
    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise MigrationError(f"La base heredada ya tiene violaciones de claves foráneas: {violations[:5]}")
    if connection.execute("SELECT 1 FROM users WHERE role NOT IN ('ADMIN', 'CITIZEN', 'RECYCLER') LIMIT 1").fetchone():
        raise MigrationError("Hay roles heredados no reconocidos; no se modificaron datos")
    if connection.execute("SELECT 1 FROM ecopoints WHERE code IS NULL LIMIT 1").fetchone():
        raise MigrationError("Hay EcoPuntos sin código; no se modificaron datos")
    mismatch_queries = (
        """SELECT d.id FROM deposits d
           JOIN users u ON u.id = d.citizen_id
           JOIN ecopoints e ON e.id = d.ecopoint_id
           JOIN compartments c ON c.id = d.compartment_id
           WHERE c.ecopoint_id != e.id OR c.material_id != d.material_id OR u.role != 'CITIZEN' LIMIT 1""",
        """SELECT c.id FROM collections c
           JOIN ecopoints e ON e.id = c.ecopoint_id
           JOIN users u ON u.id = c.recycler_id
           JOIN compartments b ON b.id = c.compartment_id
           WHERE b.ecopoint_id != e.id OR u.role != 'RECYCLER' LIMIT 1""",
        """SELECT t.id FROM point_transactions t
           JOIN deposits d ON d.id = t.deposit_id
           WHERE t.deposit_id IS NOT NULL AND t.user_id != d.citizen_id LIMIT 1""",
    )
    for query in mismatch_queries:
        if connection.execute(query).fetchone():
            raise MigrationError("Hay relaciones operativas inconsistentes; revisar antes de migrar")


def _row_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        for table in sorted(EXPECTED_TABLES)
    }


def _primary_keys(connection: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(
        row[0]
        for row in connection.execute(f'SELECT id FROM "{table}" ORDER BY id')
    )


def create_verified_backup(database_path: Path, backup_path: Path) -> str:
    database_path = database_path.resolve(strict=True)
    backup_path = backup_path.resolve()
    if database_path == backup_path:
        raise MigrationError("La ruta del respaldo no puede ser la base de origen")
    if backup_path.exists():
        raise MigrationError("El archivo de respaldo ya existe; el script no lo sobrescribe")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as source, sqlite3.connect(backup_path) as backup:
        source.backup(backup)
        check = backup.execute("PRAGMA integrity_check").fetchone()[0]
        if check != "ok":
            raise MigrationError(f"El respaldo no pasó integrity_check: {check}")
        foreign_key_issues = backup.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_issues:
            raise MigrationError(f"El respaldo tiene violaciones FK: {foreign_key_issues[:5]}")
    return hashlib.sha256(backup_path.read_bytes()).hexdigest()


def migrate_database(database_path: Path) -> dict[str, object]:
    database_path = database_path.resolve(strict=True)
    before_counts: dict[str, int]
    before_ids: dict[str, tuple[str, ...]]
    connection = sqlite3.connect(database_path, isolation_level=None)
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        if "schema_migrations" in _table_names(connection):
            already = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?", (VERSION,)
            ).fetchone()
            if already:
                return {"status": "already_applied", "version": VERSION}
        _assert_legacy_schema(connection)
        before_counts = _row_counts(connection)
        before_ids = {table: _primary_keys(connection, table) for table in EXPECTED_TABLES}
        legacy_id = LEGACY_UNIVERSITY_ID.hex
        now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ", timespec="microseconds")

        # SQLite requires foreign_keys to be disabled before BEGIN when tables
        # referenced by existing FKs are rebuilt.
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("""
                CREATE TABLE universities (
                    id CHAR(32) NOT NULL PRIMARY KEY,
                    name VARCHAR(160) NOT NULL,
                    slug VARCHAR(80) NOT NULL,
                    city VARCHAR(120) NOT NULL,
                    campus_name VARCHAR(160) NOT NULL,
                    address VARCHAR(240),
                    active BOOLEAN NOT NULL,
                    public_registration_enabled BOOLEAN NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
            """)
            connection.execute("CREATE UNIQUE INDEX ix_universities_slug ON universities(slug)")
            connection.execute("CREATE INDEX ix_universities_active ON universities(active)")
            connection.execute("CREATE INDEX ix_universities_public_registration_enabled ON universities(public_registration_enabled)")
            connection.execute(
                """INSERT INTO universities
                   (id, name, slug, city, campus_name, address, active,
                    public_registration_enabled, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (legacy_id, "Universidad legado pendiente de asignación", LEGACY_UNIVERSITY_SLUG,
                 "Bogotá", "Sede pendiente de asignación", None, 1, 0, now, now),
            )

            connection.execute("""
                CREATE TABLE users__new (
                    id CHAR(32) NOT NULL PRIMARY KEY,
                    email VARCHAR(254) NOT NULL,
                    full_name VARCHAR(120) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(16) NOT NULL,
                    university_id CHAR(32),
                    is_active BOOLEAN NOT NULL,
                    created_at DATETIME NOT NULL,
                    CONSTRAINT ck_user_role_university CHECK (
                        (role = 'ADMIN' AND university_id IS NULL) OR
                        (role IN ('CITIZEN', 'RECYCLER', 'UNIVERSITY_ADMIN') AND university_id IS NOT NULL)
                    ),
                    CONSTRAINT uq_user_id_university UNIQUE (id, university_id),
                    FOREIGN KEY(university_id) REFERENCES universities(id) ON DELETE RESTRICT
                )
            """)
            connection.execute("""
                INSERT INTO users__new
                    (id, email, full_name, password_hash, role, university_id, is_active, created_at)
                SELECT id, email, full_name, password_hash, role,
                    CASE WHEN role = 'ADMIN' THEN NULL ELSE ? END,
                    is_active, created_at
                FROM users
            """, (legacy_id,))
            connection.execute("DROP TABLE users")
            connection.execute("ALTER TABLE users__new RENAME TO users")
            connection.execute("CREATE UNIQUE INDEX ix_users_email ON users(email)")
            connection.execute("CREATE INDEX ix_users_role ON users(role)")
            connection.execute("CREATE INDEX ix_users_university_id ON users(university_id)")

            connection.execute("""
                CREATE TABLE ecopoints__new (
                    id CHAR(32) NOT NULL PRIMARY KEY,
                    code VARCHAR(40) NOT NULL,
                    university_id CHAR(32) NOT NULL,
                    name VARCHAR(120) NOT NULL,
                    address VARCHAR(240) NOT NULL,
                    active BOOLEAN NOT NULL,
                    created_at DATETIME NOT NULL,
                    CONSTRAINT uq_ecopoint_university_code UNIQUE (university_id, code),
                    CONSTRAINT uq_ecopoint_id_university UNIQUE (id, university_id),
                    FOREIGN KEY(university_id) REFERENCES universities(id) ON DELETE RESTRICT
                )
            """)
            connection.execute("""
                INSERT INTO ecopoints__new (id, code, university_id, name, address, active, created_at)
                SELECT id, code, ?, name, address, active, created_at FROM ecopoints
            """, (legacy_id,))
            connection.execute("DROP TABLE ecopoints")
            connection.execute("ALTER TABLE ecopoints__new RENAME TO ecopoints")
            connection.execute("CREATE INDEX ix_ecopoints_university_id ON ecopoints(university_id)")
            connection.execute("CREATE INDEX ix_ecopoints_active ON ecopoints(active)")

            connection.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(80) NOT NULL PRIMARY KEY,
                    applied_at DATETIME NOT NULL
                )
            """)

            from app.core.sqlite_integrity import SQLITE_INTEGRITY_TRIGGERS
            for statement in SQLITE_INTEGRITY_TRIGGERS:
                connection.execute(statement)

            after_counts = _row_counts(connection)
            after_ids = {table: _primary_keys(connection, table) for table in EXPECTED_TABLES}
            if before_counts != after_counts or before_ids != after_ids:
                raise MigrationError("Conteos o UUID cambiaron durante la migración")
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise MigrationError(f"foreign_key_check encontró violaciones: {violations[:5]}")
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise MigrationError(f"integrity_check falló: {integrity}")
            connection.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)", (VERSION, now)
            )
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        connection.execute("PRAGMA foreign_keys=ON")
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if violations or integrity != "ok":
            raise MigrationError(f"Validación posterior falló: foreign_key_check={violations[:5]}, integrity={integrity}")
        return {
            "status": "migrated",
            "version": VERSION,
            "legacy_university_id": str(LEGACY_UNIVERSITY_ID),
            "row_counts": after_counts,
            "preserved_uuid_counts": {table: len(ids) for table, ids in after_ids.items()},
            "foreign_key_check": "ok",
            "integrity_check": integrity,
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path, help="Ruta SQLite exacta a migrar")
    parser.add_argument("--backup", required=True, type=Path, help="Ruta nueva para el respaldo previo")
    args = parser.parse_args()
    try:
        database = args.database.resolve(strict=True)
        backup = args.backup.resolve()
        digest = create_verified_backup(database, backup)
        print(f"Base objetivo: {database}")
        print(f"Respaldo verificado: {backup}")
        print(f"SHA-256 respaldo: {digest}")
        confirmation = input(f"Para continuar, escribe exactamente MIGRATE {database}: ")
        if confirmation != f"MIGRATE {database}":
            print("Cancelado; no se modificó la base objetivo.")
            return 2
        result = migrate_database(database)
        print(result)
        return 0
    except (OSError, sqlite3.Error, MigrationError) as error:
        print(f"Migración detenida: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

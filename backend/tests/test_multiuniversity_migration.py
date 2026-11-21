import importlib.util
import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4


MIGRATION_PATH = Path(__file__).parents[1] / "scripts" / "migrations" / "migrate_multiuniversity_v1.py"
SPEC = importlib.util.spec_from_file_location("migrate_multiuniversity_v1", MIGRATION_PATH)
MIGRATION = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MIGRATION)


def _legacy_database(path: Path) -> dict[str, str]:
    ids = {name: uuid4().hex for name in (
        "admin", "citizen", "recycler", "material", "ecopoint", "compartment",
        "deposit", "transaction", "alert", "collection",
    )}
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript("""
            CREATE TABLE users (
                id CHAR(32) NOT NULL PRIMARY KEY, email VARCHAR(254) NOT NULL,
                full_name VARCHAR(120) NOT NULL, password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(16) NOT NULL, is_active BOOLEAN NOT NULL, created_at DATETIME NOT NULL
            );
            CREATE UNIQUE INDEX ix_users_email ON users(email);
            CREATE INDEX ix_users_role ON users(role);
            CREATE TABLE ecopoints (
                id CHAR(32) NOT NULL PRIMARY KEY, code VARCHAR(40) NOT NULL,
                name VARCHAR(120) NOT NULL, address VARCHAR(240) NOT NULL,
                active BOOLEAN NOT NULL, created_at DATETIME NOT NULL
            );
            CREATE UNIQUE INDEX ix_ecopoints_code ON ecopoints(code);
            CREATE INDEX ix_ecopoints_active ON ecopoints(active);
            CREATE TABLE materials (
                id CHAR(32) NOT NULL PRIMARY KEY, name VARCHAR(80) NOT NULL,
                description VARCHAR(300), points_per_gram NUMERIC(10, 4) NOT NULL,
                active BOOLEAN NOT NULL
            );
            CREATE TABLE compartments (
                id CHAR(32) NOT NULL PRIMARY KEY, ecopoint_id CHAR(32) NOT NULL,
                material_id CHAR(32) NOT NULL, label VARCHAR(80) NOT NULL,
                capacity_kg NUMERIC(10, 3) NOT NULL, current_kg NUMERIC(10, 3) NOT NULL,
                fill_threshold_pct INTEGER NOT NULL, active BOOLEAN NOT NULL,
                FOREIGN KEY(ecopoint_id) REFERENCES ecopoints(id),
                FOREIGN KEY(material_id) REFERENCES materials(id)
            );
            CREATE TABLE deposits (
                id CHAR(32) NOT NULL PRIMARY KEY, citizen_id CHAR(32) NOT NULL,
                ecopoint_id CHAR(32) NOT NULL, compartment_id CHAR(32) NOT NULL,
                material_id CHAR(32) NOT NULL, weight_g INTEGER NOT NULL,
                factor_applied NUMERIC(10, 4) NOT NULL, points_awarded NUMERIC(14, 4) NOT NULL,
                created_at DATETIME NOT NULL, FOREIGN KEY(citizen_id) REFERENCES users(id),
                FOREIGN KEY(ecopoint_id) REFERENCES ecopoints(id),
                FOREIGN KEY(compartment_id) REFERENCES compartments(id),
                FOREIGN KEY(material_id) REFERENCES materials(id)
            );
            CREATE TABLE point_transactions (
                id CHAR(32) NOT NULL PRIMARY KEY, user_id CHAR(32) NOT NULL,
                deposit_id CHAR(32), type VARCHAR(12) NOT NULL, amount NUMERIC(14, 4) NOT NULL,
                description VARCHAR(240) NOT NULL, created_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(deposit_id) REFERENCES deposits(id)
            );
            CREATE TABLE alerts (
                id CHAR(32) NOT NULL PRIMARY KEY, compartment_id CHAR(32) NOT NULL,
                type VARCHAR(24) NOT NULL, status VARCHAR(12) NOT NULL,
                message VARCHAR(240) NOT NULL, created_at DATETIME NOT NULL, resolved_at DATETIME,
                FOREIGN KEY(compartment_id) REFERENCES compartments(id)
            );
            CREATE TABLE collections (
                id CHAR(32) NOT NULL PRIMARY KEY, ecopoint_id CHAR(32) NOT NULL,
                compartment_id CHAR(32) NOT NULL, recycler_id CHAR(32) NOT NULL,
                weight_kg NUMERIC(10, 3) NOT NULL, status VARCHAR(16) NOT NULL,
                created_at DATETIME NOT NULL, notes TEXT,
                FOREIGN KEY(ecopoint_id) REFERENCES ecopoints(id),
                FOREIGN KEY(compartment_id) REFERENCES compartments(id),
                FOREIGN KEY(recycler_id) REFERENCES users(id)
            );
        """)
        stamp = "2026-01-01 00:00:00.000000"
        db.executemany(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (ids["admin"], "admin@example.test", "Admin", "hash-admin", "ADMIN", 1, stamp),
                (ids["citizen"], "citizen@example.test", "Citizen", "hash-citizen", "CITIZEN", 1, stamp),
                (ids["recycler"], "recycler@example.test", "Recycler", "hash-recycler", "RECYCLER", 1, stamp),
            ],
        )
        db.execute("INSERT INTO ecopoints VALUES (?, ?, ?, ?, ?, ?)",
                   (ids["ecopoint"], "LEGACY-01", "Legacy EcoPoint", "Bogotá", 1, stamp))
        db.execute("INSERT INTO materials VALUES (?, ?, ?, ?, ?)",
                   (ids["material"], "PET", "PET", "0.25", 1))
        db.execute("INSERT INTO compartments VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (ids["compartment"], ids["ecopoint"], ids["material"], "PET", "10.000", "2.000", 80, 1))
        db.execute("INSERT INTO deposits VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (ids["deposit"], ids["citizen"], ids["ecopoint"], ids["compartment"], ids["material"], 100, "0.25", "25.0000", stamp))
        db.execute("INSERT INTO point_transactions VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (ids["transaction"], ids["citizen"], ids["deposit"], "EARN", "25.0000", "deposit", stamp))
        db.execute("INSERT INTO alerts VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (ids["alert"], ids["compartment"], "FILL_THRESHOLD", "ACTIVE", "full", stamp, None))
        db.execute("INSERT INTO collections VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (ids["collection"], ids["ecopoint"], ids["compartment"], ids["recycler"], "1.000", "COMPLETED", stamp, None))
    db.close()
    return ids


def test_migration_preserves_rows_uuids_and_relations(tmp_path):
    database = tmp_path / "legacy.sqlite"
    backup = tmp_path / "legacy-backup.sqlite"
    original_ids = _legacy_database(database)
    backup_hash = MIGRATION.create_verified_backup(database, backup)
    assert len(backup_hash) == 64
    with sqlite3.connect(backup) as backup_db:
        assert backup_db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert backup_db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 3
        assert backup_db.execute("SELECT id FROM deposits").fetchone()[0] == original_ids["deposit"]
    restored = tmp_path / "restored-before-migration.sqlite"
    shutil.copy2(backup, restored)
    with sqlite3.connect(restored) as restored_db:
        assert restored_db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert restored_db.execute("SELECT id FROM collections").fetchone()[0] == original_ids["collection"]

    result = MIGRATION.migrate_database(database)
    assert result["status"] == "migrated"
    assert result["foreign_key_check"] == "ok"
    assert result["integrity_check"] == "ok"

    with sqlite3.connect(database) as db:
        users = {row[0]: row for row in db.execute(
            "SELECT id, password_hash, role, university_id FROM users"
        )}
        assert set(users) == {original_ids["admin"], original_ids["citizen"], original_ids["recycler"]}
        assert users[original_ids["admin"]][1:] == ("hash-admin", "ADMIN", None)
        legacy_id = MIGRATION.LEGACY_UNIVERSITY_ID.hex
        assert users[original_ids["citizen"]][3] == legacy_id
        assert users[original_ids["recycler"]][3] == legacy_id
        assert db.execute("SELECT id, university_id FROM ecopoints").fetchone() == (original_ids["ecopoint"], legacy_id)
        assert db.execute("SELECT citizen_id, ecopoint_id, compartment_id FROM deposits").fetchone() == (
            original_ids["citizen"], original_ids["ecopoint"], original_ids["compartment"]
        )
        assert db.execute("SELECT user_id, deposit_id FROM point_transactions").fetchone() == (
            original_ids["citizen"], original_ids["deposit"]
        )
        assert db.execute("SELECT recycler_id, ecopoint_id, compartment_id FROM collections").fetchone() == (
            original_ids["recycler"], original_ids["ecopoint"], original_ids["compartment"]
        )
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    repeated = MIGRATION.migrate_database(database)
    assert repeated == {"status": "already_applied", "version": MIGRATION.VERSION}

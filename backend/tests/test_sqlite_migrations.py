from sqlalchemy import create_engine

from app.core.sqlite_integrity import SQLITE_INTEGRITY_TRIGGERS, install_sqlite_integrity_triggers
from app.core.sqlite_migrations import upgrade_unidentified_deposits


def test_unidentified_deposit_upgrade_preserves_existing_rows_and_uuids(tmp_path):
    database = tmp_path / "legacy.sqlite"
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.exec_driver_sql("CREATE TABLE users (id CHAR(32) PRIMARY KEY)")
        connection.exec_driver_sql("CREATE TABLE ecopoints (id CHAR(32) PRIMARY KEY)")
        connection.exec_driver_sql("CREATE TABLE materials (id CHAR(32) PRIMARY KEY)")
        connection.exec_driver_sql("""CREATE TABLE compartments (
            id CHAR(32) NOT NULL PRIMARY KEY, ecopoint_id CHAR(32) NOT NULL,
            material_id CHAR(32) NOT NULL, label VARCHAR(80) NOT NULL,
            capacity_kg NUMERIC(10,3) NOT NULL CHECK(capacity_kg > 0),
            current_kg NUMERIC(10,3) NOT NULL CHECK(current_kg >= 0),
            fill_threshold_pct INTEGER NOT NULL CHECK(fill_threshold_pct > 0 AND fill_threshold_pct <= 100),
            active BOOLEAN NOT NULL,
            FOREIGN KEY(ecopoint_id) REFERENCES ecopoints(id) ON DELETE RESTRICT,
            FOREIGN KEY(material_id) REFERENCES materials(id) ON DELETE RESTRICT
        )""")
        connection.exec_driver_sql("""CREATE TABLE deposits (
            id CHAR(32) NOT NULL PRIMARY KEY, citizen_id CHAR(32) NOT NULL,
            ecopoint_id CHAR(32) NOT NULL, compartment_id CHAR(32) NOT NULL,
            material_id CHAR(32) NOT NULL, weight_g INTEGER NOT NULL CHECK(weight_g > 0),
            factor_applied NUMERIC(10,4) NOT NULL CHECK(factor_applied > 0),
            points_awarded NUMERIC(14,4) NOT NULL CHECK(points_awarded > 0),
            created_at DATETIME NOT NULL,
            FOREIGN KEY(citizen_id) REFERENCES users(id) ON DELETE RESTRICT,
            FOREIGN KEY(ecopoint_id) REFERENCES ecopoints(id) ON DELETE RESTRICT,
            FOREIGN KEY(compartment_id) REFERENCES compartments(id) ON DELETE RESTRICT,
            FOREIGN KEY(material_id) REFERENCES materials(id) ON DELETE RESTRICT
        )""")
        connection.exec_driver_sql("CREATE INDEX ix_compartments_ecopoint_id ON compartments(ecopoint_id)")
        connection.exec_driver_sql("CREATE INDEX ix_deposits_compartment_id ON deposits(compartment_id)")
        connection.exec_driver_sql("INSERT INTO users VALUES ('user-1')")
        connection.exec_driver_sql("INSERT INTO ecopoints VALUES ('point-1')")
        connection.exec_driver_sql("INSERT INTO materials VALUES ('material-1')")
        connection.exec_driver_sql("INSERT INTO compartments VALUES ('compartment-1','point-1','material-1','PET',25,1,80,1)")
        connection.exec_driver_sql("INSERT INTO deposits VALUES ('deposit-1','user-1','point-1','compartment-1','material-1',100,0.25,25,'2026-01-01')")

    assert upgrade_unidentified_deposits(engine) is True
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT id FROM compartments").scalar_one() == "compartment-1"
        assert connection.exec_driver_sql("SELECT id FROM deposits").scalar_one() == "deposit-1"
        assert connection.exec_driver_sql("PRAGMA integrity_check").scalar_one() == "ok"
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        connection.commit()
        compartment_material = next(row for row in connection.exec_driver_sql('PRAGMA table_info("compartments")') if row[1] == "material_id")
        deposit_material = next(row for row in connection.exec_driver_sql('PRAGMA table_info("deposits")') if row[1] == "material_id")
        assert compartment_material[3] == 0 and deposit_material[3] == 0
    engine.dispose()


def _dependent_trigger_legacy_database(engine):
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.exec_driver_sql("CREATE TABLE universities (id CHAR(32) PRIMARY KEY)")
        connection.exec_driver_sql("""CREATE TABLE users (
            id CHAR(32) PRIMARY KEY, university_id CHAR(32), role VARCHAR(20),
            FOREIGN KEY(university_id) REFERENCES universities(id) ON DELETE RESTRICT
        )""")
        connection.exec_driver_sql("""CREATE TABLE ecopoints (
            id CHAR(32) PRIMARY KEY, university_id CHAR(32),
            FOREIGN KEY(university_id) REFERENCES universities(id) ON DELETE RESTRICT
        )""")
        connection.exec_driver_sql("CREATE TABLE materials (id CHAR(32) PRIMARY KEY)")
        connection.exec_driver_sql("""CREATE TABLE compartments (
            id CHAR(32) NOT NULL PRIMARY KEY, ecopoint_id CHAR(32) NOT NULL,
            material_id CHAR(32) NOT NULL, label VARCHAR(80) NOT NULL,
            capacity_kg NUMERIC(10,3) NOT NULL CHECK(capacity_kg > 0),
            current_kg NUMERIC(10,3) NOT NULL CHECK(current_kg >= 0),
            fill_threshold_pct INTEGER NOT NULL CHECK(fill_threshold_pct > 0 AND fill_threshold_pct <= 100),
            active BOOLEAN NOT NULL,
            FOREIGN KEY(ecopoint_id) REFERENCES ecopoints(id) ON DELETE RESTRICT,
            FOREIGN KEY(material_id) REFERENCES materials(id) ON DELETE RESTRICT
        )""")
        connection.exec_driver_sql("""CREATE TABLE deposits (
            id CHAR(32) NOT NULL PRIMARY KEY, citizen_id CHAR(32) NOT NULL,
            ecopoint_id CHAR(32) NOT NULL, compartment_id CHAR(32) NOT NULL,
            material_id CHAR(32) NOT NULL, weight_g INTEGER NOT NULL CHECK(weight_g > 0),
            factor_applied NUMERIC(10,4) NOT NULL CHECK(factor_applied > 0),
            points_awarded NUMERIC(14,4) NOT NULL CHECK(points_awarded > 0),
            created_at DATETIME NOT NULL,
            FOREIGN KEY(citizen_id) REFERENCES users(id) ON DELETE RESTRICT,
            FOREIGN KEY(ecopoint_id) REFERENCES ecopoints(id) ON DELETE RESTRICT,
            FOREIGN KEY(compartment_id) REFERENCES compartments(id) ON DELETE RESTRICT,
            FOREIGN KEY(material_id) REFERENCES materials(id) ON DELETE RESTRICT
        )""")
        connection.exec_driver_sql("""CREATE TABLE collections (
            id CHAR(32) PRIMARY KEY, recycler_id CHAR(32) NOT NULL,
            ecopoint_id CHAR(32) NOT NULL, compartment_id CHAR(32) NOT NULL
        )""")
        connection.exec_driver_sql("CREATE TABLE alerts (id CHAR(32) PRIMARY KEY, compartment_id CHAR(32))")
        connection.exec_driver_sql("""CREATE TABLE point_transactions (
            id CHAR(32) PRIMARY KEY, user_id CHAR(32), deposit_id CHAR(32)
        )""")
        connection.exec_driver_sql("CREATE INDEX ix_compartments_ecopoint_id ON compartments(ecopoint_id)")
        connection.exec_driver_sql("CREATE INDEX ix_compartments_material_id ON compartments(material_id)")
        connection.exec_driver_sql("CREATE INDEX ix_deposits_citizen_id ON deposits(citizen_id)")
        connection.exec_driver_sql("CREATE INDEX ix_deposits_ecopoint_id ON deposits(ecopoint_id)")
        connection.exec_driver_sql("CREATE INDEX ix_deposits_compartment_id ON deposits(compartment_id)")
        connection.exec_driver_sql("CREATE INDEX ix_deposits_material_id ON deposits(material_id)")
        connection.exec_driver_sql("CREATE INDEX ix_deposits_created_at ON deposits(created_at)")
        connection.exec_driver_sql("INSERT INTO universities VALUES ('university-1')")
        connection.exec_driver_sql("INSERT INTO users VALUES ('citizen-1','university-1','CITIZEN')")
        connection.exec_driver_sql("INSERT INTO ecopoints VALUES ('ecopoint-1','university-1')")
        connection.exec_driver_sql("INSERT INTO materials VALUES ('material-1')")
        connection.exec_driver_sql("""INSERT INTO compartments VALUES
            ('compartment-1','ecopoint-1','material-1','PET',25,1,80,1)""")
        connection.exec_driver_sql("""INSERT INTO deposits VALUES
            ('deposit-1','citizen-1','ecopoint-1','compartment-1','material-1',100,0.25,25,'2026-01-01')""")
    install_sqlite_integrity_triggers(engine)


def _trigger_map(connection):
    return dict(connection.exec_driver_sql(
        "SELECT name, sql FROM sqlite_master WHERE type='trigger' ORDER BY name"
    ).all())


def _index_map(connection, table):
    indexes = {}
    for row in connection.exec_driver_sql(f'PRAGMA index_list("{table}")'):
        indexes[row[1]] = connection.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (row[1],)
        ).scalar_one_or_none()
    return indexes


def _foreign_key_map(connection, table):
    return tuple(sorted(tuple(row[1:]) for row in connection.exec_driver_sql(f'PRAGMA foreign_key_list("{table}")')))


def test_unidentified_upgrade_preserves_all_dependent_triggers_and_is_idempotent(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'dependent-triggers.sqlite'}")
    _dependent_trigger_legacy_database(engine)
    with engine.connect() as connection:
        trigger_definitions = _trigger_map(connection)
        assert len(trigger_definitions) == len(SQLITE_INTEGRITY_TRIGGERS)
        assert "trg_collections_university_insert" in trigger_definitions
        indexes_before = {table: _index_map(connection, table) for table in ("compartments", "deposits")}
        foreign_keys_before = {table: _foreign_key_map(connection, table) for table in ("compartments", "deposits")}
        counts_before = {
            table: connection.exec_driver_sql(f'SELECT COUNT(*) FROM "{table}"').scalar_one()
            for table in ("compartments", "deposits")
        }

    assert upgrade_unidentified_deposits(engine) is True
    with engine.connect() as connection:
        assert _trigger_map(connection) == trigger_definitions
        assert {table: _index_map(connection, table) for table in indexes_before} == indexes_before
        assert {table: _foreign_key_map(connection, table) for table in foreign_keys_before} == foreign_keys_before
        assert connection.exec_driver_sql("SELECT id FROM compartments").scalar_one() == "compartment-1"
        assert connection.exec_driver_sql("SELECT id FROM deposits").scalar_one() == "deposit-1"
        assert {
            table: connection.exec_driver_sql(f'SELECT COUNT(*) FROM "{table}"').scalar_one()
            for table in counts_before
        } == counts_before
        assert connection.exec_driver_sql("PRAGMA integrity_check").scalar_one() == "ok"
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        connection.commit()
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.exec_driver_sql("INSERT INTO users VALUES ('recycler-1','university-1','RECYCLER')")
        connection.exec_driver_sql("""INSERT INTO compartments VALUES
            ('compartment-unknown','ecopoint-1',NULL,'No identificados',25,0,80,1)""")
        connection.exec_driver_sql("""INSERT INTO deposits VALUES
            ('deposit-unknown','citizen-1','ecopoint-1','compartment-unknown',NULL,250,0,0,'2026-01-02')""")
        connection.exec_driver_sql("""INSERT INTO collections VALUES
            ('collection-1','recycler-1','ecopoint-1','compartment-unknown')""")
        assert connection.exec_driver_sql(
            "SELECT material_id, factor_applied, points_awarded FROM deposits WHERE id='deposit-unknown'"
        ).one() == (None, 0, 0)
        assert connection.exec_driver_sql("PRAGMA integrity_check").scalar_one() == "ok"
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        connection.commit()

    assert upgrade_unidentified_deposits(engine) is False
    with engine.connect() as connection:
        assert _trigger_map(connection) == trigger_definitions
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM compartments").scalar_one() == 2
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM deposits").scalar_one() == 2
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM collections").scalar_one() == 1
        assert connection.exec_driver_sql("PRAGMA integrity_check").scalar_one() == "ok"
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    engine.dispose()

"""Data-preserving SQLite schema upgrades required by the application."""

import re

from sqlalchemy.engine import Connection, Engine


_REBUILT_TABLES = frozenset({"compartments", "deposits"})
_DEPENDENCY_PATTERN = re.compile(r"\b(?:compartments|deposits)\b", re.IGNORECASE)
_USER_REFERENCE_PATTERN = re.compile(r"\busers\b", re.IGNORECASE)
_ASSIGNMENT_REFERENCE_PATTERN = re.compile(r"\brecycler_assignments\b", re.IGNORECASE)


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _table_names(connection: Connection) -> set[str]:
    return {
        row[0]
        for row in connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def _table_rows(connection: Connection, table: str) -> tuple[tuple[object, ...], ...]:
    quoted = _quote_identifier(table)
    return tuple(
        tuple(row)
        for row in connection.exec_driver_sql(f"SELECT * FROM {quoted} ORDER BY id")
    )


def _foreign_key_signature(connection: Connection, table: str) -> tuple[tuple[object, ...], ...]:
    quoted = _quote_identifier(table)
    rows = connection.exec_driver_sql(f"PRAGMA foreign_key_list({quoted})").all()
    # PRAGMA's numeric FK id reflects declaration order, not FK identity.
    # Compare the actual relationship and action semantics instead.
    return tuple(sorted(tuple(row[1:]) for row in rows))


def _foreign_key_clauses(connection: Connection, table: str) -> list[str]:
    """Recreate the table's current FK declarations, including composite keys."""
    groups: dict[int, list[tuple[object, ...]]] = {}
    for row in connection.exec_driver_sql(f"PRAGMA foreign_key_list({_quote_identifier(table)})"):
        groups.setdefault(row[0], []).append(tuple(row))

    clauses: list[str] = []
    for group in groups.values():
        group.sort(key=lambda row: row[1])
        target_table = _quote_identifier(str(group[0][2]))
        source_columns = ", ".join(_quote_identifier(str(row[3])) for row in group)
        target_columns = [row[4] for row in group]
        clause = f"FOREIGN KEY ({source_columns}) REFERENCES {target_table}"
        if all(column is not None for column in target_columns):
            clause += " (" + ", ".join(_quote_identifier(str(column)) for column in target_columns) + ")"
        on_update = str(group[0][5]).upper()
        on_delete = str(group[0][6]).upper()
        match = str(group[0][7]).upper()
        if on_update != "NO ACTION":
            clause += f" ON UPDATE {on_update}"
        if on_delete != "NO ACTION":
            clause += f" ON DELETE {on_delete}"
        if match != "NONE":
            clause += f" MATCH {match}"
        clauses.append(clause)
    return clauses


def _index_signature(connection: Connection, table: str) -> tuple[tuple[object, ...], ...]:
    quoted = _quote_identifier(table)
    signature = []
    for row in connection.exec_driver_sql(f"PRAGMA index_list({quoted})"):
        name = str(row[1])
        sql = connection.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (name,)
        ).scalar_one_or_none()
        columns = tuple(
            info[2]
            for info in connection.exec_driver_sql(f"PRAGMA index_info({_quote_identifier(name)})")
        )
        signature.append((name, bool(row[2]), row[3], bool(row[4]), sql, columns))
    return tuple(sorted(signature, key=lambda item: item[0]))


def _trigger_definitions(connection: Connection) -> dict[str, tuple[str, str]]:
    return {
        str(name): (str(table_name), str(sql))
        for name, table_name, sql in connection.exec_driver_sql(
            "SELECT name, tbl_name, sql FROM sqlite_master "
            "WHERE type='trigger' AND sql IS NOT NULL ORDER BY name"
        )
    }


def _triggers_referencing_users(connection: Connection) -> dict[str, tuple[str, str]]:
    return {
        name: (table, sql)
        for name, (table, sql) in _trigger_definitions(connection).items()
        if table.lower() == "users" or _USER_REFERENCE_PATTERN.search(sql)
    }


def _foreign_keys_referencing_table(
    connection: Connection, target_table: str
) -> tuple[tuple[object, ...], ...]:
    references = []
    for table in _table_names(connection):
        for row in connection.exec_driver_sql(
            f"PRAGMA foreign_key_list({_quote_identifier(table)})"
        ):
            if str(row[2]).lower() == target_table.lower():
                references.append((table, *tuple(row[1:])))
    return tuple(sorted(references, key=repr))


def _rebuild_recycler_assignments_organization_fk(connection: Connection) -> None:
    """Ensure organization_id references organizations with explicit RESTRICT.

    SQLite cannot alter an existing FK action in place. Recreate the original
    table DDL, changing only that action, while retaining rows, indexes, triggers
    and all other constraints verbatim.
    """
    fk_rows = connection.exec_driver_sql(
        'PRAGMA foreign_key_list("recycler_assignments")'
    ).all()
    organization_fks = [row for row in fk_rows if row[3] == "organization_id"]
    if len(organization_fks) > 1:
        raise RuntimeError("recycler_assignments tiene varias FK para organization_id; revisión manual requerida")
    if organization_fks:
        fk = organization_fks[0]
        if str(fk[2]).lower() != "organizations" or str(fk[4]).lower() != "id":
            raise RuntimeError("La FK de recycler_assignments.organization_id apunta a una tabla o columna inesperada")
        if str(fk[6]).upper() == "RESTRICT":
            return

    original = connection.exec_driver_sql(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='recycler_assignments'"
    ).scalar_one_or_none()
    if original is None:
        raise RuntimeError("No se encontró recycler_assignments para corregir su FK")
    if "recycler_assignments__new" in _table_names(connection):
        raise RuntimeError("Existe recycler_assignments__new; revisión manual requerida")

    create_prefix = re.match(
        r'(?is)^\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?'
        r'(?:"recycler_assignments"|`recycler_assignments`|\[recycler_assignments\]|recycler_assignments)\b',
        original,
    )
    if create_prefix is None:
        raise RuntimeError("No se pudo identificar la definición de recycler_assignments")
    replacement = "CREATE TABLE recycler_assignments__new" + original[create_prefix.end():]
    reference_pattern = re.compile(
        r'(?is)(REFERENCES\s+(?:"organizations"|`organizations`|\[organizations\]|organizations)'
        r'\s*\(\s*(?:"id"|`id`|\[id\]|id)\s*\))'
        r'(\s+ON\s+DELETE\s+(?:NO\s+ACTION|RESTRICT|CASCADE|SET\s+NULL|SET\s+DEFAULT))?'
    )
    replacement, substitutions = reference_pattern.subn(r"\1 ON DELETE RESTRICT", replacement)
    if substitutions != 1:
        raise RuntimeError(
            "No se encontró exactamente una FK recycler_assignments.organization_id → organizations.id"
        )

    names = [str(row[1]) for row in connection.exec_driver_sql('PRAGMA table_info("recycler_assignments")')]
    rows_before = _table_rows(connection, "recycler_assignments")
    indexes_before = _index_signature(connection, "recycler_assignments")
    foreign_keys_before = _foreign_key_signature(connection, "recycler_assignments")
    all_triggers_before = _trigger_definitions(connection)
    dependent_triggers = {
        name: definition for name, definition in all_triggers_before.items()
        if definition[0].lower() == "recycler_assignments"
        or _ASSIGNMENT_REFERENCE_PATTERN.search(definition[1])
    }
    indexes_sql = connection.exec_driver_sql(
        "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='recycler_assignments' AND sql IS NOT NULL"
    ).scalars().all()
    for trigger_name in dependent_triggers:
        connection.exec_driver_sql(f"DROP TRIGGER {_quote_identifier(trigger_name)}")

    connection.exec_driver_sql(replacement)
    quoted_names = ", ".join(_quote_identifier(name) for name in names)
    connection.exec_driver_sql(
        f"INSERT INTO recycler_assignments__new ({quoted_names}) "
        f"SELECT {quoted_names} FROM recycler_assignments"
    )
    connection.exec_driver_sql("DROP TABLE recycler_assignments")
    connection.exec_driver_sql("ALTER TABLE recycler_assignments__new RENAME TO recycler_assignments")
    for statement in indexes_sql:
        connection.exec_driver_sql(statement)
    for _trigger_name, (_table_name, definition) in dependent_triggers.items():
        connection.exec_driver_sql(definition)

    rows_after = _table_rows(connection, "recycler_assignments")
    indexes_after = _index_signature(connection, "recycler_assignments")
    foreign_keys_after = _foreign_key_signature(connection, "recycler_assignments")
    triggers_after = _trigger_definitions(connection)
    if rows_before != rows_after:
        raise RuntimeError("La migración no preservó las filas de recycler_assignments")
    if indexes_before != indexes_after:
        raise RuntimeError("La migración no preservó los índices de recycler_assignments")
    if foreign_keys_before != foreign_keys_after:
        # Exactly one action may change: the organization_id FK to RESTRICT.
        before_without_action = tuple(sorted((
            tuple("RESTRICT" if index == 5 and row[1:4] == ("organizations", "organization_id", "id") else value
                  for index, value in enumerate(row))
            for row in foreign_keys_before
        ), key=repr))
        if before_without_action != foreign_keys_after:
            raise RuntimeError("La migración modificó claves foráneas distintas a la acción de organization_id")
    if all_triggers_before != triggers_after:
        raise RuntimeError("La migración no restauró las definiciones originales de triggers")
    expected = [row for row in connection.exec_driver_sql('PRAGMA foreign_key_list("recycler_assignments")') if row[3] == "organization_id"]
    if len(expected) != 1 or str(expected[0][6]).upper() != "RESTRICT":
        raise RuntimeError("La FK de recycler_assignments.organization_id no quedó con ON DELETE RESTRICT")
    violations = connection.exec_driver_sql("PRAGMA foreign_key_check").all()
    if violations:
        raise RuntimeError(f"La reconstrucción dejó claves foráneas inválidas: {violations[:5]}")


def _table_counts(connection: Connection, tables: set[str]) -> dict[str, int]:
    return {
        table: int(connection.exec_driver_sql(
            f"SELECT COUNT(*) FROM {_quote_identifier(table)}"
        ).scalar_one())
        for table in tables
    }


def _check_is_upgraded(connection: Connection) -> bool:
    compartment_columns = connection.exec_driver_sql('PRAGMA table_info("compartments")').all()
    deposit_columns = connection.exec_driver_sql('PRAGMA table_info("deposits")').all()
    compartment_material = next((row[3] for row in compartment_columns if row[1] == "material_id"), None)
    deposit_material = next((row[3] for row in deposit_columns if row[1] == "material_id"), None)
    deposit_sql = connection.exec_driver_sql(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='deposits'"
    ).scalar_one()
    compartment_sql = connection.exec_driver_sql(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='compartments'"
    ).scalar_one()
    if compartment_material is None or deposit_material is None:
        raise RuntimeError("No se encontró material_id en compartments o deposits; revisión manual requerida")
    return (
        not compartment_material
        and not deposit_material
        and "ck_deposit_reward_matches_material" in deposit_sql
        and "ck_unidentified_compartment_label" in compartment_sql
    )


def upgrade_unidentified_deposits(engine: Engine) -> bool:
    """Allow unidentified compartments/deposits without losing dependent triggers.

    SQLite validates the whole schema on ALTER TABLE ... RENAME. A trigger on a
    different table can therefore block the rename if its body references the
    table being replaced. Dependent triggers are saved and dropped inside the
    same IMMEDIATE transaction, then restored verbatim before integrity checks.
    """
    if engine.dialect.name != "sqlite":
        return False

    connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        # SQLite only allows this pragma to change outside a transaction.
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        if connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() != 0:
            raise RuntimeError("No fue posible desactivar FK para reconstruir tablas SQLite")

        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            tables = _table_names(connection)
            if not _REBUILT_TABLES.issubset(tables):
                connection.exec_driver_sql("COMMIT")
                return False
            if {"compartments__new", "deposits__new"}.intersection(tables):
                raise RuntimeError("Hay tablas temporales de migración; revisión manual requerida")
            if _check_is_upgraded(connection):
                connection.exec_driver_sql("COMMIT")
                return False

            compartment_columns = connection.exec_driver_sql('PRAGMA table_info("compartments")').all()
            deposit_columns = connection.exec_driver_sql('PRAGMA table_info("deposits")').all()
            compartment_material_notnull = next(row[3] for row in compartment_columns if row[1] == "material_id")
            deposit_material_notnull = next(row[3] for row in deposit_columns if row[1] == "material_id")
            if not compartment_material_notnull or not deposit_material_notnull:
                raise RuntimeError("Esquema de compartments/deposits parcialmente actualizado; revisión manual requerida")

            counts_before = _table_counts(connection, tables)
            rows_before = {table: _table_rows(connection, table) for table in _REBUILT_TABLES}
            indexes_before = {
                table: _index_signature(connection, table) for table in _REBUILT_TABLES
            }
            foreign_keys_before = {
                table: _foreign_key_signature(connection, table) for table in _REBUILT_TABLES
            }
            triggers_before = _trigger_definitions(connection)
            dependent_triggers = {
                name: definition
                for name, definition in triggers_before.items()
                if definition[0] in _REBUILT_TABLES
                or _DEPENDENCY_PATTERN.search(definition[1])
            }
            compartment_indexes = connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL",
                ("compartments",),
            ).scalars().all()
            deposit_indexes = connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL",
                ("deposits",),
            ).scalars().all()
            compartment_foreign_keys = _foreign_key_clauses(connection, "compartments")
            deposit_foreign_keys = _foreign_key_clauses(connection, "deposits")

            for trigger_name in dependent_triggers:
                connection.exec_driver_sql(
                    f"DROP TRIGGER {_quote_identifier(trigger_name)}"
                )

            compartment_fk_sql = ",\n" + ",\n".join(compartment_foreign_keys) if compartment_foreign_keys else ""
            connection.exec_driver_sql(f"""
                CREATE TABLE compartments__new (
                    id CHAR(32) NOT NULL PRIMARY KEY,
                    ecopoint_id CHAR(32) NOT NULL,
                    material_id CHAR(32),
                    label VARCHAR(80) NOT NULL,
                    capacity_kg NUMERIC(10, 3) NOT NULL,
                    current_kg NUMERIC(10, 3) NOT NULL,
                    fill_threshold_pct INTEGER NOT NULL,
                    active BOOLEAN NOT NULL,
                    CONSTRAINT ck_compartment_capacity_positive CHECK (capacity_kg > 0),
                    CONSTRAINT ck_compartment_weight_nonnegative CHECK (current_kg >= 0),
                    CONSTRAINT ck_compartment_threshold_range CHECK (fill_threshold_pct > 0 AND fill_threshold_pct <= 100),
                    CONSTRAINT ck_unidentified_compartment_label CHECK (material_id IS NOT NULL OR label = 'No identificados')
                    {compartment_fk_sql}
                )
            """)
            connection.exec_driver_sql("""
                INSERT INTO compartments__new
                    (id, ecopoint_id, material_id, label, capacity_kg, current_kg, fill_threshold_pct, active)
                SELECT id, ecopoint_id, material_id, label, capacity_kg, current_kg, fill_threshold_pct, active
                FROM compartments
            """)
            connection.exec_driver_sql("DROP TABLE compartments")
            connection.exec_driver_sql("ALTER TABLE compartments__new RENAME TO compartments")
            for statement in compartment_indexes:
                connection.exec_driver_sql(statement)

            deposit_fk_sql = ",\n" + ",\n".join(deposit_foreign_keys) if deposit_foreign_keys else ""
            connection.exec_driver_sql(f"""
                CREATE TABLE deposits__new (
                    id CHAR(32) NOT NULL PRIMARY KEY,
                    citizen_id CHAR(32) NOT NULL,
                    ecopoint_id CHAR(32) NOT NULL,
                    compartment_id CHAR(32) NOT NULL,
                    material_id CHAR(32),
                    weight_g INTEGER NOT NULL,
                    factor_applied NUMERIC(10, 4) NOT NULL,
                    points_awarded NUMERIC(14, 4) NOT NULL,
                    created_at DATETIME NOT NULL,
                    CONSTRAINT ck_deposit_weight_positive CHECK (weight_g > 0),
                    CONSTRAINT ck_deposit_reward_matches_material CHECK (
                        (material_id IS NULL AND factor_applied = 0 AND points_awarded = 0) OR
                        (material_id IS NOT NULL AND factor_applied > 0 AND points_awarded > 0)
                    )
                    {deposit_fk_sql}
                )
            """)
            connection.exec_driver_sql("""
                INSERT INTO deposits__new
                    (id, citizen_id, ecopoint_id, compartment_id, material_id, weight_g,
                     factor_applied, points_awarded, created_at)
                SELECT id, citizen_id, ecopoint_id, compartment_id, material_id, weight_g,
                       factor_applied, points_awarded, created_at
                FROM deposits
            """)
            connection.exec_driver_sql("DROP TABLE deposits")
            connection.exec_driver_sql("ALTER TABLE deposits__new RENAME TO deposits")
            for statement in deposit_indexes:
                connection.exec_driver_sql(statement)

            for _trigger_name, (_table_name, definition) in dependent_triggers.items():
                connection.exec_driver_sql(definition)

            counts_after = _table_counts(connection, tables)
            rows_after = {table: _table_rows(connection, table) for table in _REBUILT_TABLES}
            indexes_after = {
                table: _index_signature(connection, table) for table in _REBUILT_TABLES
            }
            foreign_keys_after = {
                table: _foreign_key_signature(connection, table) for table in _REBUILT_TABLES
            }
            triggers_after = _trigger_definitions(connection)
            if counts_before != counts_after or rows_before != rows_after:
                raise RuntimeError("La migración no preservó todos los registros de compartments/deposits")
            if indexes_before != indexes_after:
                raise RuntimeError("La migración no preservó los índices de compartments/deposits")
            if foreign_keys_before != foreign_keys_after:
                raise RuntimeError("La migración no preservó las claves foráneas de compartments/deposits")
            if triggers_before != triggers_after:
                raise RuntimeError("La migración no preservó todas las definiciones de triggers")

            violations = connection.exec_driver_sql("PRAGMA foreign_key_check").all()
            integrity = connection.exec_driver_sql("PRAGMA integrity_check").scalar_one()
            if violations or integrity != "ok":
                raise RuntimeError(
                    f"Validación SQLite fallida: FK={violations[:5]}, integrity={integrity}"
                )
            connection.exec_driver_sql("COMMIT")
            return True
        except Exception:
            connection.exec_driver_sql("ROLLBACK")
            raise
    finally:
        try:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        finally:
            connection.close()


def _upgrade_recycler_module_columns(connection: Connection) -> bool:
    changed = False
    tables = _table_names(connection)
    if "recycler_profiles" in tables:
        profile_columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info("recycler_profiles")')}
        if "link_type" not in profile_columns:
            connection.exec_driver_sql("ALTER TABLE recycler_profiles ADD COLUMN link_type VARCHAR(12) NOT NULL DEFAULT 'INDEPENDENT'")
            changed = True
            if "organization_id" in profile_columns:
                connection.exec_driver_sql("UPDATE recycler_profiles SET link_type='ORGANIZATION' WHERE organization_id IS NOT NULL")
        if "document_type" not in profile_columns:
            connection.exec_driver_sql("ALTER TABLE recycler_profiles ADD COLUMN document_type VARCHAR(20)")
            changed = True
        if "document_number" not in profile_columns:
            connection.exec_driver_sql("ALTER TABLE recycler_profiles ADD COLUMN document_number VARCHAR(40)")
            changed = True
        if "status" not in profile_columns:
            connection.exec_driver_sql("ALTER TABLE recycler_profiles ADD COLUMN status VARCHAR(12) NOT NULL DEFAULT 'ACTIVE'")
            changed = True
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_recycler_profiles_organization_id "
            "ON recycler_profiles(organization_id)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_recycler_profiles_status ON recycler_profiles(status)"
        )
    if "recycler_assignments" in tables:
        assignment_columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info("recycler_assignments")')}
        if "organization_id" not in assignment_columns:
            connection.exec_driver_sql("ALTER TABLE recycler_assignments ADD COLUMN organization_id CHAR(32) REFERENCES organizations(id) ON DELETE RESTRICT")
            changed = True
        if "origin" not in assignment_columns:
            connection.exec_driver_sql("ALTER TABLE recycler_assignments ADD COLUMN origin VARCHAR(12) NOT NULL DEFAULT 'DIRECT'")
            changed = True
        assignment_foreign_keys = connection.exec_driver_sql(
            'PRAGMA foreign_key_list("recycler_assignments")'
        ).all()
        organization_fks = [row for row in assignment_foreign_keys if row[3] == "organization_id"]
        if not organization_fks:
            raise RuntimeError("recycler_assignments.organization_id existe sin la FK esperada; revisión manual requerida")
        if any(row[2] != "organizations" or row[4] != "id" for row in organization_fks):
            raise RuntimeError(
                "recycler_assignments.organization_id existe sin la FK esperada; revisión manual requerida"
            )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_recycler_assignments_organization_id "
            "ON recycler_assignments(organization_id)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_recycler_assignments_origin "
            "ON recycler_assignments(origin)"
        )
        if str(organization_fks[0][6]).upper() != "RESTRICT":
            _rebuild_recycler_assignments_organization_fk(connection)
            changed = True
    if "collections" in tables:
        collection_columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info("collections")')}
        if "material_id" not in collection_columns:
            connection.exec_driver_sql("ALTER TABLE collections ADD COLUMN material_id CHAR(32) REFERENCES materials(id) ON DELETE RESTRICT")
            changed = True
        collection_foreign_keys = connection.exec_driver_sql(
            'PRAGMA foreign_key_list("collections")'
        ).all()
        if not any(row[3] == "material_id" and row[2] == "materials" and row[4] == "id"
                   for row in collection_foreign_keys):
            raise RuntimeError(
                "collections.material_id existe sin la FK esperada; revisión manual requerida"
            )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_collections_material_id ON collections(material_id)"
        )
    return changed


def upgrade_recycler_university_optional(engine: Engine) -> bool:
    """Allow RECYCLER rows without university_id while preserving all user rows.

    Deliberately not invoked during application startup. Deploy only after a verified
    backup and explicit operator action; it does not assign legacy user scopes.
    """
    if engine.dialect.name != "sqlite":
        return False
    connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        if connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() != 1:
            raise RuntimeError("La migración requiere claves foráneas SQLite activas")
        # Keep enforcement enabled while rebuilding users. Defer validation until
        # the replacement table has its final name so dependent rows stay intact.
        connection.exec_driver_sql("PRAGMA defer_foreign_keys=ON")
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            original = connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
            ).scalar_one_or_none()
            if original is None:
                connection.exec_driver_sql("COMMIT")
                return False
            old_to_new_clauses = (
                (
                    "(role IN ('CITIZEN', 'RECYCLER') AND university_id IS NOT NULL)",
                    "(role = 'CITIZEN' AND university_id IS NOT NULL) OR (role = 'RECYCLER')",
                ),
                (
                    "(role IN ('CITIZEN', 'RECYCLER', 'UNIVERSITY_ADMIN') AND university_id IS NOT NULL)",
                    "(role IN ('CITIZEN', 'UNIVERSITY_ADMIN') AND university_id IS NOT NULL) OR (role = 'RECYCLER')",
                ),
            )
            matched_clause = next(
                ((old, new) for old, new in old_to_new_clauses if old in original), None
            )
            if matched_clause is None:
                # Current schemas may omit the legacy role or retain UNIVERSITY_ADMIN;
                # in either form RECYCLER must be independently nullable.
                current_recycler_clause = "(role = 'RECYCLER')"
                if current_recycler_clause in original:
                    module_changed = _upgrade_recycler_module_columns(connection)
                    connection.exec_driver_sql("COMMIT")
                    return module_changed
                raise RuntimeError("Restricción de users desconocida; revisión manual requerida")
            old_clause, new_clause = matched_clause
            columns = connection.exec_driver_sql('PRAGMA table_info("users")').all()
            names = [str(row[1]) for row in columns]
            indexes = connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='users' AND sql IS NOT NULL"
            ).scalars().all()
            dependent_triggers = _triggers_referencing_users(connection)
            foreign_keys_to_users_before = _foreign_keys_referencing_table(connection, "users")
            before = tuple(tuple(row) for row in connection.exec_driver_sql("SELECT * FROM users ORDER BY id"))
            replacement = original.replace('CREATE TABLE users', 'CREATE TABLE users__new', 1).replace(old_clause, new_clause, 1)
            if replacement == original:
                replacement = original.replace('CREATE TABLE "users"', 'CREATE TABLE "users__new"', 1).replace(old_clause, new_clause, 1)
            if replacement == original:
                raise RuntimeError("No se pudo preparar la tabla users; revisión manual requerida")

            # SQLite reparses triggers attached to other tables when the replacement
            # table is renamed. Temporarily drop every trigger that references users
            # (including triggers attached to users); the surrounding transaction
            # restores these DDL changes automatically if anything fails.
            for trigger_name in dependent_triggers:
                connection.exec_driver_sql(
                    f"DROP TRIGGER {_quote_identifier(trigger_name)}"
                )

            connection.exec_driver_sql(replacement)
            quoted = ", ".join(_quote_identifier(name) for name in names)
            connection.exec_driver_sql(f"INSERT INTO users__new ({quoted}) SELECT {quoted} FROM users")
            connection.exec_driver_sql("DROP TABLE users")
            connection.exec_driver_sql("ALTER TABLE users__new RENAME TO users")
            for statement in indexes:
                connection.exec_driver_sql(statement)
            _upgrade_recycler_module_columns(connection)
            for _trigger_name, (_table_name, definition) in dependent_triggers.items():
                connection.exec_driver_sql(definition)
            after = tuple(tuple(row) for row in connection.exec_driver_sql("SELECT * FROM users ORDER BY id"))
            if before != after:
                raise RuntimeError("La migración modificó filas de users")
            triggers_after = _triggers_referencing_users(connection)
            if triggers_after != dependent_triggers:
                raise RuntimeError("La migración no restauró todas las definiciones de triggers que usan users")
            foreign_keys_to_users_after = _foreign_keys_referencing_table(connection, "users")
            if foreign_keys_to_users_after != foreign_keys_to_users_before:
                raise RuntimeError("La migración modificó claves foráneas que apuntan a users")
            violations = connection.exec_driver_sql("PRAGMA foreign_key_check").all()
            if violations:
                raise RuntimeError(f"La migración dejó claves foráneas inválidas: {violations[:5]}")
            # Replacing a referenced SQLite parent table can leave the engine's
            # deferred-FK counter stale even after the final schema/data pass its
            # explicit check. Clear deferred mode only after proving there are no
            # violations, then commit with FK enforcement still enabled.
            connection.exec_driver_sql("PRAGMA defer_foreign_keys=OFF")
            connection.exec_driver_sql("COMMIT")
            return True
        except Exception:
            connection.exec_driver_sql("ROLLBACK")
            raise
    finally:
        try:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        finally:
            connection.close()

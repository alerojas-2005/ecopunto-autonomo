"""Copy a complete EcoPunto SQLite database into an empty PostgreSQL database.

The source is opened read-only. The destination is never truncated or dropped.
Repeated runs are accepted only when every destination row exactly matches the
source; partial or different destination data causes an abort.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import MetaData, Table, create_engine, func, inspect, select
from sqlalchemy.engine import Engine, URL
from sqlalchemy.dialects import sqlite
from sqlalchemy.sql.sqltypes import Enum as SAEnum
from sqlalchemy.types import Uuid

from app.core.postgres_integrity import install_postgres_integrity_triggers
from app.models import entities  # noqa: F401 - register model metadata
from app.core.database import Base


class MigrationError(RuntimeError):
    pass


def _normalize_sql(value: str | None) -> str | None:
    if value is None:
        return None
    return "".join(value.replace('"', "").replace("`", "").replace("[", "").replace("]", "").split()).rstrip(";").lower()


def _normalize_fk_action(action: str | None) -> str:
    """Canonicalize SQLite's omitted/default action without conflating RESTRICT."""
    return (action or "NO ACTION").strip().upper()


def _validate_table_constraints(inspector, mapped: Table, source: Engine) -> None:
    name = mapped.name
    errors: list[str] = []

    expected_pk = tuple(column.name for column in mapped.primary_key.columns)
    actual_pk = tuple(inspector.get_pk_constraint(name).get("constrained_columns") or ())
    if actual_pk != expected_pk:
        errors.append(f"PK esperada={expected_pk}, real={actual_pk}")

    expected_fks = {
        (fk.parent.name, fk.column.table.name, fk.column.name, _normalize_fk_action(fk.ondelete))
        for fk in mapped.foreign_keys
    }
    quoted_name = name.replace('"', '""')
    with source.connect() as connection:
        actual_fks = {
            (str(row[3]), str(row[2]), str(row[4]), _normalize_fk_action(row[6]))
            for row in connection.exec_driver_sql(f'PRAGMA foreign_key_list("{quoted_name}")')
        }
    if actual_fks != expected_fks:
        errors.append(f"FK faltantes={sorted(expected_fks-actual_fks)}, adicionales={sorted(actual_fks-expected_fks)}")

    expected_unique = {
        (tuple(column.name for column in constraint.columns), None)
        for constraint in mapped.constraints if constraint.__class__.__name__ == "UniqueConstraint"
    }
    expected_unique.update(
        ((column.name,), None)
        for column in mapped.columns if column.unique and not column.index
    )
    actual_unique = {
        (tuple(item.get("column_names") or ()), None)
        for item in inspector.get_unique_constraints(name)
    }
    for index in inspector.get_indexes(name):
        if index.get("unique"):
            predicate = index.get("dialect_options", {}).get("sqlite_where")
            actual_unique.add((tuple(index.get("column_names") or ()), _normalize_sql(str(predicate)) if predicate is not None else None))
    for index in mapped.indexes:
        if index.unique:
            predicate = index.dialect_options["sqlite"].get("where")
            expected_unique.add((tuple(column.name for column in index.columns), _normalize_sql(str(predicate)) if predicate is not None else None))
    if actual_unique != expected_unique:
        errors.append(f"UNIQUE faltantes={sorted(expected_unique-actual_unique, key=str)}, adicionales={sorted(actual_unique-expected_unique, key=str)}")

    expected_checks = {
        _normalize_sql(str(constraint.sqltext.compile(dialect=sqlite.dialect())))
        for constraint in mapped.constraints if constraint.__class__.__name__ == "CheckConstraint"
    }
    actual_checks = {_normalize_sql(item.get("sqltext")) for item in inspector.get_check_constraints(name)}
    if actual_checks != expected_checks:
        errors.append(f"CHECK faltantes={sorted(expected_checks-actual_checks)}, adicionales={sorted(actual_checks-expected_checks)}")

    expected_indexes = {
        (index.name, tuple(column.name for column in index.columns), bool(index.unique),
         _normalize_sql(str(index.dialect_options["sqlite"].get("where"))) if index.dialect_options["sqlite"].get("where") is not None else None)
        for index in mapped.indexes
    }
    actual_indexes = {
        (index.get("name"), tuple(index.get("column_names") or ()), bool(index.get("unique")),
         _normalize_sql(str(index.get("dialect_options", {}).get("sqlite_where"))) if index.get("dialect_options", {}).get("sqlite_where") is not None else None)
        for index in inspector.get_indexes(name)
    }
    if actual_indexes != expected_indexes:
        errors.append(f"índices faltantes={sorted(expected_indexes-actual_indexes, key=str)}, adicionales={sorted(actual_indexes-expected_indexes, key=str)}")

    if errors:
        raise MigrationError(f"Restricciones incompatibles en {name}: " + "; ".join(errors))


def _source_engine(path: Path) -> Engine:
    try:
        resolved = path.expanduser().resolve(strict=True)
    except OSError as error:
        raise MigrationError(f"No se puede resolver el archivo SQLite de origen: {path}") from error
    if not resolved.is_file():
        raise MigrationError(f"No existe el archivo SQLite de origen: {resolved}")
    # Build a standards-based absolute file URI. Keep URI options in SQLAlchemy's
    # URL query (not inside the database path); this matters on Windows, where
    # drive letters and backslashes otherwise become part of an invalid filename.
    database_uri = f"{resolved.as_uri()}?mode=ro"
    return create_engine(URL.create(
        "sqlite+pysqlite", database=database_uri, query={"uri": "true"},
    ), pool_pre_ping=True)


def _validate_source(source: Engine) -> MetaData:
    inspector = inspect(source)
    expected_tables = set(Base.metadata.tables)
    actual_tables = set(inspector.get_table_names())
    extra = actual_tables - expected_tables
    missing = expected_tables - actual_tables
    if extra or missing:
        raise MigrationError(f"El esquema SQLite no coincide con los modelos; faltan={sorted(missing)}, sobran={sorted(extra)}")

    reflected = MetaData()
    reflected.reflect(bind=source)
    for name, mapped in Base.metadata.tables.items():
        source_table = reflected.tables[name]
        source_columns = set(source_table.columns.keys())
        mapped_columns = set(mapped.columns.keys())
        if source_columns != mapped_columns:
            raise MigrationError(
                f"Columnas incompatibles en {name}; faltan={sorted(mapped_columns-source_columns)}, "
                f"sobran={sorted(source_columns-mapped_columns)}. Actualiza una copia SQLite con su migración aprobada."
            )
        source_columns_info = {column["name"]: column for column in inspector.get_columns(name)}
        for column in mapped.columns:
            reflected_column = source_columns_info[column.name]
            actual_nullable = reflected_column.get("nullable")
            if bool(actual_nullable) != bool(column.nullable):
                raise MigrationError(
                    f"Nulabilidad incompatible en {name}.{column.name}: "
                    f"modelo nullable={column.nullable}, SQLite nullable={actual_nullable}"
                )
            expected_type = "".join(column.type.compile(dialect=sqlite.dialect()).upper().split())
            actual_type = "".join(str(reflected_column["type"]).upper().split())
            if actual_type != expected_type:
                raise MigrationError(
                    f"Tipo incompatible en {name}.{column.name}: "
                    f"modelo={expected_type}, SQLite={actual_type}"
                )
        _validate_table_constraints(inspector, mapped, source)
    with source.connect() as connection:
        connection.exec_driver_sql("PRAGMA query_only=ON")
        integrity = connection.exec_driver_sql("PRAGMA integrity_check").scalar_one()
        violations = connection.exec_driver_sql("PRAGMA foreign_key_check").all()
        if integrity != "ok" or violations:
            raise MigrationError(f"SQLite no supera validación: integrity_check={integrity!r}, foreign_key_check={len(violations)}")
    return reflected


def preflight(source: Engine) -> dict[str, int]:
    """Read-only schema and data-integrity check; never opens a destination."""
    reflected = _validate_source(source)
    with source.connect() as connection:
        connection.exec_driver_sql("PRAGMA query_only=ON")
        return {
            table.name: connection.scalar(select(func.count()).select_from(reflected.tables[table.name]))
            for table in Base.metadata.sorted_tables
        }


def _coerce(value: Any, target_type: Any) -> Any:
    if value is None:
        return None
    if isinstance(target_type, Uuid):
        return value if isinstance(value, UUID) else UUID(str(value))
    if isinstance(target_type, SAEnum) and target_type.enum_class is not None:
        return value if isinstance(value, target_type.enum_class) else target_type.enum_class(value)
    return value


def _canonical(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        return normalized.isoformat(timespec="microseconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, bytes):
        return value.hex()
    return value


def _table_digest(rows: list[dict[str, Any]], columns: list[str]) -> str:
    canonical_rows = [
        {column: _canonical(row[column]) for column in columns}
        for row in rows
    ]
    canonical_rows.sort(key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False))
    payload = json.dumps(canonical_rows, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _source_rows(connection, source_table: Table, mapped: Table) -> list[dict[str, Any]]:
    names = list(mapped.columns.keys())
    return [
        {name: _coerce(row[name], mapped.c[name].type) for name in names}
        for row in connection.execute(select(source_table)).mappings()
    ]


def _target_rows(connection, mapped: Table) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(select(mapped)).mappings()]


def migrate(source: Engine, destination: Engine, *, require_postgres: bool = True) -> dict[str, int]:
    """Create schema and copy rows; test suites may pass SQLite for destination."""
    if require_postgres and destination.dialect.name != "postgresql":
        raise MigrationError("El destino debe ser PostgreSQL (postgresql+psycopg://)")
    reflected = _validate_source(source)

    # create_all is additive: it never drops/replaces destination objects.
    Base.metadata.create_all(destination)
    tables = list(Base.metadata.sorted_tables)
    source_tables = [reflected.tables[table.name] for table in tables]
    counts: dict[str, int] = {}

    # Target data and all inserts share one transaction. An error rolls back the
    # entire copy; schema objects remain empty and can be retried safely.
    with source.connect() as source_connection, destination.begin() as target_connection:
        existing_counts = {
            table.name: target_connection.scalar(select(func.count()).select_from(table))
            for table in tables
        }
        has_data = any(existing_counts.values())
        if has_data:
            for mapped, source_table in zip(tables, source_tables, strict=True):
                expected = _source_rows(source_connection, source_table, mapped)
                actual = _target_rows(target_connection, mapped)
                if len(expected) != len(actual) or _table_digest(expected, list(mapped.columns.keys())) != _table_digest(actual, list(mapped.columns.keys())):
                    raise MigrationError(
                        f"El destino ya contiene datos diferentes o parciales en {mapped.name}; no se sobrescribió nada"
                    )
                counts[mapped.name] = len(actual)
        else:
            for mapped, source_table in zip(tables, source_tables, strict=True):
                rows = _source_rows(source_connection, source_table, mapped)
                for offset in range(0, len(rows), 1000):
                    target_connection.execute(mapped.insert(), rows[offset:offset + 1000])
                counts[mapped.name] = len(rows)

            for mapped, source_table in zip(tables, source_tables, strict=True):
                expected_count = source_connection.scalar(select(func.count()).select_from(source_table))
                actual_count = target_connection.scalar(select(func.count()).select_from(mapped))
                if expected_count != actual_count:
                    raise MigrationError(f"Conteo distinto en {mapped.name}: origen={expected_count}, destino={actual_count}")
            if destination.dialect.name == "postgresql":
                target_connection.exec_driver_sql("SET CONSTRAINTS ALL IMMEDIATE")

    if destination.dialect.name == "postgresql":
        # Install guards only after copying, so historical rows are preserved as
        # stored while all future application writes receive equivalent checks.
        install_postgres_integrity_triggers(destination)
        with destination.connect() as connection:
            invalid = connection.exec_driver_sql(
                "SELECT count(*) FROM pg_constraint WHERE contype = 'f' AND NOT convalidated"
            ).scalar_one()
            if invalid:
                raise MigrationError(f"PostgreSQL tiene {invalid} claves foráneas sin validar")
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Archivo SQLite de origen, abierto en solo lectura")
    parser.add_argument(
        "--destination-url", default=os.getenv("SUPABASE_DATABASE_URL"),
        help="URL postgresql+psycopg:// del destino; por defecto SUPABASE_DATABASE_URL",
    )
    parser.add_argument(
        "--preflight-only", action="store_true",
        help="Validar solo SQLite (tablas, columnas, nulabilidad, restricciones, índices e integridad); no conectar al destino",
    )
    args = parser.parse_args()
    if not args.preflight_only and not args.destination_url:
        parser.error("Indica --destination-url o configura SUPABASE_DATABASE_URL")
    source = _source_engine(args.source)
    if args.preflight_only:
        try:
            counts = preflight(source)
            print("Prevalidación SQLite correcta (solo lectura):")
            for table, count in counts.items():
                print(f"  {table}: {count}")
            print("Esquema coincidente; integrity_check=ok; foreign_key_check=sin errores.")
            return 0
        except MigrationError as error:
            print(f"Prevalidación fallida: {error}")
            return 1
        finally:
            source.dispose()
    destination = create_engine(args.destination_url, pool_pre_ping=True)
    try:
        results = migrate(source, destination)
        print("Migración verificada (filas por tabla):")
        for table, count in results.items():
            print(f"  {table}: {count}")
        return 0
    except MigrationError as error:
        print(f"Migración abortada: {error}")
        return 1
    except Exception as error:
        # Driver exceptions may embed connection URLs; don't echo them to logs.
        print(f"Migración abortada por un error inesperado ({type(error).__name__}). Revisa el log local protegido.")
        return 1
    finally:
        source.dispose()
        destination.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

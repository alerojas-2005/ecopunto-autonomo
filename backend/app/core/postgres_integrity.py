"""PostgreSQL equivalents of the cross-row guards used by SQLite."""

from sqlalchemy.engine import Engine


POSTGRES_INTEGRITY_DDL = (
    """
    CREATE OR REPLACE FUNCTION ecopunto_guard_deposit_resource() RETURNS trigger AS $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM users u JOIN ecopoints e ON e.university_id = u.university_id
        JOIN compartments c ON c.ecopoint_id = e.id AND c.id = NEW.compartment_id
          AND c.material_id IS NOT DISTINCT FROM NEW.material_id
        WHERE u.id = NEW.citizen_id AND u.role = 'CITIZEN' AND e.id = NEW.ecopoint_id
      ) THEN RAISE EXCEPTION 'deposit university or resource mismatch'; END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS trg_deposits_university_insert ON deposits",
    "DROP TRIGGER IF EXISTS trg_deposits_university_update ON deposits",
    "CREATE TRIGGER trg_deposits_university_insert BEFORE INSERT ON deposits FOR EACH ROW EXECUTE FUNCTION ecopunto_guard_deposit_resource()",
    "CREATE TRIGGER trg_deposits_university_update BEFORE UPDATE OF citizen_id, ecopoint_id, compartment_id, material_id ON deposits FOR EACH ROW EXECUTE FUNCTION ecopunto_guard_deposit_resource()",
    """
    CREATE OR REPLACE FUNCTION ecopunto_guard_collection_authorization() RETURNS trigger AS $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM users u JOIN ecopoints e ON e.id = NEW.ecopoint_id
        JOIN compartments c ON c.ecopoint_id = e.id AND c.id = NEW.compartment_id
          AND c.material_id IS NOT DISTINCT FROM NEW.material_id
        LEFT JOIN recycler_profiles rp ON rp.user_id = u.id
        WHERE u.id = NEW.recycler_id AND u.role = 'RECYCLER' AND u.is_active
          AND (rp.user_id IS NULL OR rp.status = 'ACTIVE')
          AND (
            EXISTS (SELECT 1 FROM recycler_assignments ra WHERE ra.recycler_id = u.id
              AND ra.status = 'ACTIVE' AND ra.starts_at <= CURRENT_TIMESTAMP
              AND (ra.ends_at IS NULL OR ra.ends_at >= CURRENT_TIMESTAMP)
              AND (ra.ecopoint_id = e.id OR ra.ecopoint_id IS NULL)
              AND ra.university_id = e.university_id
              AND ((ra.origin = 'DIRECT' AND (rp.user_id IS NULL OR (rp.link_type = 'INDEPENDENT' AND rp.organization_id IS NULL)))
                OR (ra.origin = 'AUTOMATIC' AND rp.link_type = 'ORGANIZATION' AND ra.organization_id = rp.organization_id
                  AND EXISTS (SELECT 1 FROM organizations o WHERE o.id = ra.organization_id AND o.status = 'ACTIVE'))))
            OR ((rp.user_id IS NULL OR (rp.link_type = 'INDEPENDENT' AND rp.organization_id IS NULL))
              AND u.university_id IS NOT NULL AND u.university_id = e.university_id
              AND NOT EXISTS (SELECT 1 FROM recycler_assignments ra WHERE ra.recycler_id = u.id))
          )
      ) THEN RAISE EXCEPTION 'collection university or resource mismatch'; END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS trg_collections_university_insert ON collections",
    "DROP TRIGGER IF EXISTS trg_collections_university_update ON collections",
    "CREATE TRIGGER trg_collections_university_insert BEFORE INSERT ON collections FOR EACH ROW EXECUTE FUNCTION ecopunto_guard_collection_authorization()",
    "CREATE TRIGGER trg_collections_university_update BEFORE UPDATE OF recycler_id, ecopoint_id, compartment_id, material_id ON collections FOR EACH ROW EXECUTE FUNCTION ecopunto_guard_collection_authorization()",
    """
    CREATE OR REPLACE FUNCTION ecopunto_guard_transaction_owner() RETURNS trigger AS $$
    BEGIN
      IF NEW.deposit_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM deposits d WHERE d.id = NEW.deposit_id AND d.citizen_id = NEW.user_id)
      THEN RAISE EXCEPTION 'point transaction user does not own deposit'; END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS trg_point_transactions_deposit_guard ON point_transactions",
    """
    CREATE TRIGGER trg_point_transactions_deposit_guard BEFORE INSERT OR UPDATE OF user_id, deposit_id
    ON point_transactions FOR EACH ROW EXECUTE FUNCTION ecopunto_guard_transaction_owner()
    """,
    """
    CREATE OR REPLACE FUNCTION ecopunto_guard_user_history() RETURNS trigger AS $$
    BEGIN
      IF (OLD.university_id IS DISTINCT FROM NEW.university_id AND
          (EXISTS (SELECT 1 FROM deposits WHERE citizen_id = OLD.id) OR EXISTS (SELECT 1 FROM collections WHERE recycler_id = OLD.id)))
        OR (NEW.role <> 'CITIZEN' AND EXISTS (SELECT 1 FROM deposits WHERE citizen_id = OLD.id))
        OR (NEW.role <> 'RECYCLER' AND EXISTS (SELECT 1 FROM collections WHERE recycler_id = OLD.id))
      THEN RAISE EXCEPTION 'cannot reassign user with operational history'; END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS trg_users_history_guard ON users",
    "CREATE TRIGGER trg_users_history_guard BEFORE UPDATE OF role, university_id ON users FOR EACH ROW EXECUTE FUNCTION ecopunto_guard_user_history()",
    """
    CREATE OR REPLACE FUNCTION ecopunto_guard_ecopoint_history() RETURNS trigger AS $$
    BEGIN
      IF OLD.university_id IS DISTINCT FROM NEW.university_id AND
        (EXISTS (SELECT 1 FROM deposits WHERE ecopoint_id = OLD.id) OR EXISTS (SELECT 1 FROM collections WHERE ecopoint_id = OLD.id)
         OR EXISTS (SELECT 1 FROM compartments c JOIN alerts a ON a.compartment_id = c.id WHERE c.ecopoint_id = OLD.id))
      THEN RAISE EXCEPTION 'cannot reassign ecopoint with operational history'; END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS trg_ecopoints_history_guard ON ecopoints",
    "CREATE TRIGGER trg_ecopoints_history_guard BEFORE UPDATE OF university_id ON ecopoints FOR EACH ROW EXECUTE FUNCTION ecopunto_guard_ecopoint_history()",
    """
    CREATE OR REPLACE FUNCTION ecopunto_guard_compartment_history() RETURNS trigger AS $$
    BEGIN
      IF (OLD.ecopoint_id IS DISTINCT FROM NEW.ecopoint_id OR OLD.material_id IS DISTINCT FROM NEW.material_id)
        AND (EXISTS (SELECT 1 FROM deposits WHERE compartment_id = OLD.id) OR EXISTS (SELECT 1 FROM collections WHERE compartment_id = OLD.id)
          OR EXISTS (SELECT 1 FROM alerts WHERE compartment_id = OLD.id))
      THEN RAISE EXCEPTION 'cannot reassign compartment with operational history'; END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS trg_compartments_history_guard ON compartments",
    "CREATE TRIGGER trg_compartments_history_guard BEFORE UPDATE OF ecopoint_id, material_id ON compartments FOR EACH ROW EXECUTE FUNCTION ecopunto_guard_compartment_history()",
    """
    CREATE OR REPLACE FUNCTION ecopunto_guard_deposit_owner_history() RETURNS trigger AS $$
    BEGIN
      IF EXISTS (SELECT 1 FROM point_transactions t WHERE t.deposit_id = OLD.id AND t.user_id <> NEW.citizen_id)
      THEN RAISE EXCEPTION 'cannot change deposit owner while transactions reference it'; END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS trg_deposits_owner_history_guard ON deposits",
    "CREATE TRIGGER trg_deposits_owner_history_guard BEFORE UPDATE OF citizen_id ON deposits FOR EACH ROW EXECUTE FUNCTION ecopunto_guard_deposit_owner_history()",
)


def install_postgres_integrity_triggers(engine: Engine) -> None:
    """Install/reconcile PostgreSQL integrity guards after mapped tables exist."""
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as connection:
        for statement in POSTGRES_INTEGRITY_DDL:
            connection.exec_driver_sql(statement)

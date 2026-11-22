"""SQLite-only cross-university integrity triggers.

These triggers complement service-layer validation. Revisit them if the project
moves to a database engine other than SQLite.
"""

from sqlalchemy.engine import Engine


SQLITE_INTEGRITY_TRIGGERS = (
    """
    CREATE TRIGGER IF NOT EXISTS trg_deposits_university_insert
    BEFORE INSERT ON deposits
    WHEN NOT EXISTS (
        SELECT 1
        FROM users u
        JOIN ecopoints e ON e.university_id = u.university_id
        JOIN compartments c ON c.ecopoint_id = e.id
            AND c.id = NEW.compartment_id
            AND ((c.material_id IS NULL AND NEW.material_id IS NULL) OR c.material_id = NEW.material_id)
        WHERE u.id = NEW.citizen_id AND u.role = 'CITIZEN' AND e.id = NEW.ecopoint_id
    )
    BEGIN
        SELECT RAISE(ABORT, 'deposit university or resource mismatch');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_deposits_university_update
    BEFORE UPDATE OF citizen_id, ecopoint_id, compartment_id, material_id ON deposits
    WHEN NOT EXISTS (
        SELECT 1
        FROM users u
        JOIN ecopoints e ON e.university_id = u.university_id
        JOIN compartments c ON c.ecopoint_id = e.id
            AND c.id = NEW.compartment_id
            AND ((c.material_id IS NULL AND NEW.material_id IS NULL) OR c.material_id = NEW.material_id)
        WHERE u.id = NEW.citizen_id AND u.role = 'CITIZEN' AND e.id = NEW.ecopoint_id
    )
    BEGIN
        SELECT RAISE(ABORT, 'deposit university or resource mismatch');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_collections_university_insert
    BEFORE INSERT ON collections
    WHEN NOT EXISTS (
        SELECT 1
        FROM users u
        JOIN ecopoints e ON e.id = NEW.ecopoint_id
        JOIN compartments c ON c.ecopoint_id = e.id
            AND c.id = NEW.compartment_id
            AND c.material_id IS NEW.material_id
        LEFT JOIN recycler_profiles rp ON rp.user_id = u.id
        WHERE u.id = NEW.recycler_id AND u.role = 'RECYCLER' AND u.is_active = 1
            AND (rp.user_id IS NULL OR rp.status = 'ACTIVE')
            AND (
                EXISTS (
                    SELECT 1 FROM recycler_assignments ra
                    WHERE ra.recycler_id = u.id AND ra.status = 'ACTIVE'
                        AND datetime(ra.starts_at) <= CURRENT_TIMESTAMP
                        AND (ra.ends_at IS NULL OR datetime(ra.ends_at) >= CURRENT_TIMESTAMP)
                        AND (
                            (ra.ecopoint_id = e.id OR ra.ecopoint_id IS NULL)
                            AND ra.university_id = e.university_id
                        )
                        AND (
                            (ra.origin = 'DIRECT' AND (rp.user_id IS NULL OR
                                (rp.link_type = 'INDEPENDENT' AND rp.organization_id IS NULL)))
                            OR (ra.origin = 'AUTOMATIC' AND rp.link_type = 'ORGANIZATION'
                                AND ra.organization_id = rp.organization_id
                                AND EXISTS (SELECT 1 FROM organizations o
                                    WHERE o.id = ra.organization_id AND o.status = 'ACTIVE'))
                        )
                )
                OR (
                    (rp.user_id IS NULL OR
                        (rp.link_type = 'INDEPENDENT' AND rp.organization_id IS NULL))
                    AND u.university_id IS NOT NULL AND u.university_id = e.university_id
                    AND NOT EXISTS (
                        SELECT 1 FROM recycler_assignments ra WHERE ra.recycler_id = u.id
                    )
                )
            )
    )
    BEGIN
        SELECT RAISE(ABORT, 'collection university or resource mismatch');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_collections_university_update
    BEFORE UPDATE OF recycler_id, ecopoint_id, compartment_id, material_id ON collections
    WHEN NOT EXISTS (
        SELECT 1
        FROM users u
        JOIN ecopoints e ON e.id = NEW.ecopoint_id
        JOIN compartments c ON c.ecopoint_id = e.id
            AND c.id = NEW.compartment_id
            AND c.material_id IS NEW.material_id
        LEFT JOIN recycler_profiles rp ON rp.user_id = u.id
        WHERE u.id = NEW.recycler_id AND u.role = 'RECYCLER' AND u.is_active = 1
            AND (rp.user_id IS NULL OR rp.status = 'ACTIVE')
            AND (
                EXISTS (
                    SELECT 1 FROM recycler_assignments ra
                    WHERE ra.recycler_id = u.id AND ra.status = 'ACTIVE'
                        AND datetime(ra.starts_at) <= CURRENT_TIMESTAMP
                        AND (ra.ends_at IS NULL OR datetime(ra.ends_at) >= CURRENT_TIMESTAMP)
                        AND (
                            (ra.ecopoint_id = e.id OR ra.ecopoint_id IS NULL)
                            AND ra.university_id = e.university_id
                        )
                        AND (
                            (ra.origin = 'DIRECT' AND (rp.user_id IS NULL OR
                                (rp.link_type = 'INDEPENDENT' AND rp.organization_id IS NULL)))
                            OR (ra.origin = 'AUTOMATIC' AND rp.link_type = 'ORGANIZATION'
                                AND ra.organization_id = rp.organization_id
                                AND EXISTS (SELECT 1 FROM organizations o
                                    WHERE o.id = ra.organization_id AND o.status = 'ACTIVE'))
                        )
                )
                OR (
                    (rp.user_id IS NULL OR
                        (rp.link_type = 'INDEPENDENT' AND rp.organization_id IS NULL))
                    AND u.university_id IS NOT NULL AND u.university_id = e.university_id
                    AND NOT EXISTS (
                        SELECT 1 FROM recycler_assignments ra WHERE ra.recycler_id = u.id
                    )
                )
            )
    )
    BEGIN
        SELECT RAISE(ABORT, 'collection university or resource mismatch');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_point_transactions_deposit_insert
    BEFORE INSERT ON point_transactions
    WHEN NEW.deposit_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM deposits d
        WHERE d.id = NEW.deposit_id AND d.citizen_id = NEW.user_id
    )
    BEGIN
        SELECT RAISE(ABORT, 'point transaction user does not own deposit');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_point_transactions_deposit_update
    BEFORE UPDATE OF user_id, deposit_id ON point_transactions
    WHEN NEW.deposit_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM deposits d
        WHERE d.id = NEW.deposit_id AND d.citizen_id = NEW.user_id
    )
    BEGIN
        SELECT RAISE(ABORT, 'point transaction user does not own deposit');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_users_role_or_tenant_reassignment
    BEFORE UPDATE OF role, university_id ON users
    WHEN (
        (OLD.university_id IS NOT NEW.university_id AND (
            EXISTS (SELECT 1 FROM deposits d WHERE d.citizen_id = OLD.id)
            OR EXISTS (SELECT 1 FROM collections c WHERE c.recycler_id = OLD.id)
        ))
        OR (NEW.role != 'CITIZEN' AND EXISTS (SELECT 1 FROM deposits d WHERE d.citizen_id = OLD.id))
        OR (NEW.role != 'RECYCLER' AND EXISTS (SELECT 1 FROM collections c WHERE c.recycler_id = OLD.id))
    )
    BEGIN
        SELECT RAISE(ABORT, 'cannot reassign user with operational history');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_ecopoints_tenant_reassignment
    BEFORE UPDATE OF university_id ON ecopoints
    WHEN OLD.university_id IS NOT NEW.university_id AND (
        EXISTS (SELECT 1 FROM deposits d WHERE d.ecopoint_id = OLD.id)
        OR EXISTS (SELECT 1 FROM collections c WHERE c.ecopoint_id = OLD.id)
        OR EXISTS (
            SELECT 1 FROM compartments c JOIN alerts a ON a.compartment_id = c.id
            WHERE c.ecopoint_id = OLD.id
        )
    )
    BEGIN
        SELECT RAISE(ABORT, 'cannot reassign ecopoint with operational history');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_compartments_resource_reassignment
    BEFORE UPDATE OF ecopoint_id, material_id ON compartments
    WHEN (OLD.ecopoint_id IS NOT NEW.ecopoint_id OR OLD.material_id IS NOT NEW.material_id)
        AND (
            EXISTS (SELECT 1 FROM deposits d WHERE d.compartment_id = OLD.id)
            OR EXISTS (SELECT 1 FROM collections c WHERE c.compartment_id = OLD.id)
            OR EXISTS (SELECT 1 FROM alerts a WHERE a.compartment_id = OLD.id)
        )
    BEGIN
        SELECT RAISE(ABORT, 'cannot reassign compartment with operational history');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_deposit_owner_update_preserves_transactions
    BEFORE UPDATE OF citizen_id ON deposits
    WHEN EXISTS (
        SELECT 1 FROM point_transactions t
        WHERE t.deposit_id = OLD.id AND t.user_id != NEW.citizen_id
    )
    BEGIN
        SELECT RAISE(ABORT, 'cannot change deposit owner while transactions reference it');
    END
    """,
)


def install_sqlite_integrity_triggers(engine: Engine) -> None:
    """Install trigger protections after tables exist; safe to call repeatedly."""
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as connection:
        # Refresh deposit and collection guards so existing databases receive the
        # current resource and authorization checks on application startup.
        connection.exec_driver_sql("DROP TRIGGER IF EXISTS trg_deposits_university_insert")
        connection.exec_driver_sql("DROP TRIGGER IF EXISTS trg_deposits_university_update")
        # Refresh collection guards when their authorization/material rules change.
        connection.exec_driver_sql("DROP TRIGGER IF EXISTS trg_collections_university_insert")
        connection.exec_driver_sql("DROP TRIGGER IF EXISTS trg_collections_university_update")
        for statement in SQLITE_INTEGRITY_TRIGGERS:
            connection.exec_driver_sql(statement)

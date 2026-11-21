# EcoPunto multi-university: Phase A migration

Phase A adds the `universities` table, associates existing users and EcoPuntos
with the temporary `universidad-legado-pendiente` university, and introduces
SQLite integrity triggers. The legacy university is operational (`active=1`)
but is not available for public signup (`public_registration_enabled=0`).

## Important compatibility boundary

Public signup with university selection is deferred to Phase B. The current
`POST /auth/register` contract does not accept a university. With the Phase A
role/university constraint, it cannot create a citizen until that endpoint is
updated in Phase B. Provisioning university-bound users through existing user
creation flows also requires Phase B changes.

Do not start the updated API against an unmigrated existing database. The
application's `create_all()` creates missing tables but does not add columns to
existing tables. Run the migration on a verified copy first.

## Rehearse before a real migration

The migration script requires explicit database and backup paths, creates a
non-overwriting SQLite backup, verifies its integrity and foreign keys, and
asks for the exact target path before changing the selected database. Rehearse
it only on a restored copy first:

```powershell
cd backend
python scripts/migrations/migrate_multiuniversity_v1.py `
  --database C:\path\to\isolated-copy.sqlite `
  --backup C:\path\to\isolated-copy-before-migration.sqlite
```

The target must be an existing EcoPunto SQLite database with the expected
legacy schema. The script reports row counts, preserved UUID counts,
`foreign_key_check`, and `integrity_check`. It records migration version
`0001_multiuniversity` and is safe to invoke again after that version is
recorded.

For a real migration, stop all writers, identify the SQLite file actually used
by the service (`DATABASE_URL` may be relative to the backend working
directory), create and restore-test a separate backup, rehearse on a copy, and
only then schedule the same versioned migration for the verified target. Do not
delete the pre-migration backup until post-migration verification is accepted.

The cross-row integrity triggers are SQLite-specific. Reassess or replace them
with equivalent constraints if the application changes database engines.

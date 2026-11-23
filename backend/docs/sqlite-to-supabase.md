# Migración SQLite a PostgreSQL (Supabase)

El procedimiento está en `scripts/migrate_sqlite_to_postgres.py`. Abre el SQLite
en modo de solo lectura, valida el esquema y `integrity_check`/`foreign_key_check`,
crea las tablas mapeadas sin borrar objetos y copia las filas en orden FK dentro de
una transacción PostgreSQL. Conserva IDs, hashes de contraseñas, fechas y valores
numéricos. Nunca ejecuta seed ni actualiza el origen.

El destino debe estar vacío en las tablas de EcoPunto. Una segunda ejecución
compara el contenido fila por fila y devuelve los conteos si coincide exactamente;
datos parciales o distintos causan un aborto sin sobrescritura. Si el esquema de
origen no coincide con los modelos actuales, el script se detiene: migra primero
una copia SQLite con el procedimiento SQLite aprobado y vuelve a validar esa copia.

PostgreSQL recibe restricciones/índices del metadata SQLAlchemy, incluido el
índice único parcial de alertas. `app/core/postgres_integrity.py` instala los
triggers PostgreSQL equivalentes para validación de depósitos y colecciones,
propiedad de transacciones y protección del historial. Los triggers se instalan
después de copiar los registros históricos y también durante startup de FastAPI.

## Ejecución

Instalar dependencias desde `backend`:

```powershell
python -m pip install -r requirements.txt
```

Configurar la URI del proyecto Supabase en la sesión actual, sin guardarla en el
repositorio ni compartirla en terminales/logs:

```powershell
$env:SUPABASE_DATABASE_URL = 'postgresql+psycopg://<usuario>:<contraseña>@<host>:5432/<base>?sslmode=require'
```

Tras verificar que el destino es el proyecto correcto y está vacío, ejecutar:

```powershell
python scripts/migrate_sqlite_to_postgres.py --source 'C:\ruta\ecopunto.db'
```

El script no acepta SQLite como destino en CLI. Una conexión fallida no imprime
la URI. Conservar una copia de seguridad del origen y validar los conteos
reportados antes de apuntar la aplicación al destino con `DATABASE_URL`.

## Validación previa al cambio de tráfico

### Prevalidación sin conectar a Supabase

Desde el directorio `backend`, ejecuta:

```powershell
.\.venv312\Scripts\python.exe scripts\migrate_sqlite_to_postgres.py `
  --source ..\backups\ecopunto_pre_despliegue.db `
  --preflight-only
```

Este modo abre el archivo con SQLite `mode=ro`, compara tablas y columnas con
`Base.metadata`, comprueba nulabilidad, claves primarias y foráneas, restricciones
`UNIQUE`/`CHECK` e índices modelados, y ejecuta `PRAGMA integrity_check` y
`PRAGMA foreign_key_check`. Imprime los conteos de todas las tablas. No requiere ni
lee `SUPABASE_DATABASE_URL`, no crea un engine de destino, no crea tablas y no copia
filas. El éxito se indica con `Prevalidación SQLite correcta (solo lectura)` y
`Esquema coincidente; integrity_check=ok; foreign_key_check=sin errores.` Las
diferencias producen código de salida distinto de cero y un detalle de la tabla o
restricción.

Comparar en origen y destino conteos de todas las tablas del informe, IDs UUID,
hashes de contraseña, asignaciones y relaciones históricas. Confirmar que las
claves foráneas PostgreSQL están validadas y probar login, consultas multiuniversidad,
depósitos, recolecciones autorizadas y las restricciones de historial en el entorno
de demostración. Esta migración de datos no publica la aplicación ni cambia por sí
sola `DATABASE_URL`.

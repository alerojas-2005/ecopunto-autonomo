# Backend de EcoPunto Autónomo

API inicial para registrar depósitos, administrar puntos de reciclaje, calcular EcoPuntos, gestionar alertas y registrar recolecciones. Está construida con FastAPI, SQLAlchemy 2, Pydantic y SQLite. Las fechas se guardan y exponen en UTC.

## Requisitos

- Python 3.11 o posterior.
- Windows PowerShell (los comandos también pueden adaptarse a otros sistemas).

Las dependencias del proyecto están declaradas en `requirements.txt`. No se instalan globalmente; los comandos siguientes crean un entorno virtual dentro de `backend/`.

## Instalación en Windows PowerShell

Desde la raíz del repositorio:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Si PowerShell bloquea la activación de scripts, se puede omitir la activación y usar directamente `\.venv\Scripts\python.exe` en los comandos siguientes.

## Configuración

Edita `backend/.env` (no se debe versionar), agrega `JWT_SECRET_KEY=<clave_generada>` y reemplaza el marcador por una clave aleatoria larga. Una forma de generarla en PowerShell:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Configura `BOOTSTRAP_ADMIN_TOKEN` con otro valor aleatorio si vas a crear el primer administrador mediante el endpoint de inicialización. Sin ese valor, el endpoint de bootstrap devuelve 404. El bootstrap solo funciona mientras no exista ningún administrador. La ruta y el token no crean usuarios con una contraseña preestablecida.

Variables disponibles:

| Variable | Uso | Valor de ejemplo |
| --- | --- | --- |
| `DATABASE_URL` | Base de datos SQLAlchemy | `sqlite:///./ecopunto.db` |
| `JWT_SECRET_KEY` | Firma de tokens JWT | una clave aleatoria de 48 bytes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración de token | `30` |
| `CORS_ORIGINS` | Orígenes permitidos (formato JSON) | `["http://localhost:5173","http://127.0.0.1:5173"]` |
| `BOOTSTRAP_ADMIN_TOKEN` | Clave temporal para crear el primer administrador | vacío hasta configurarla |

Si no se configura `JWT_SECRET_KEY`, se crea una clave aleatoria solo para el proceso actual. Los tokens dejan de ser válidos al reiniciar el servidor; en un entorno persistente debe configurarse una clave estable y privada.

## Base de datos y datos de demostración

Al iniciar la aplicación se crean las tablas que falten. Para preparar datos idempotentes de demostración (materiales Aluminio y PET, un EcoPunto y dos compartimentos), ejecuta desde `backend/`:

```powershell
python -m app.seed
```

El seed no crea usuarios ni contraseñas. Los factores de ejemplo son 0.50 puntos/gramo para Aluminio y 0.25 puntos/gramo para PET.

## Crear el administrador inicial

1. Configura `BOOTSTRAP_ADMIN_TOKEN` y `JWT_SECRET_KEY` en `.env`.
2. Inicia el servidor y llama al endpoint una vez, usando una contraseña propia de al menos 12 caracteres:

```powershell
$body = @{ email = 'admin@ejemplo.com'; full_name = 'Administración EcoPunto'; password = 'UnaClavePropiaLarga123!' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/bootstrap-admin -Headers @{ 'X-Bootstrap-Token' = 'EL_TOKEN_CONFIGURADO' } -ContentType 'application/json' -Body $body
```

Al crear el administrador, el endpoint queda deshabilitado por diseño. Los recicladores deben ser provisionados por una operación administrativa segura; no existe registro público con roles privilegiados.

## Ejecutar el servidor

Desde `backend/` con el entorno virtual activado:

```powershell
python -m uvicorn app.main:app --reload
```

La API queda en `http://127.0.0.1:8000`, la documentación interactiva en `http://127.0.0.1:8000/docs` y la comprobación simple de estado en `/health`.

## Ejecutar las pruebas

Desde `backend/`:

```powershell
python -m pytest -q
```

La suite utiliza una base SQLite en memoria e independiente; no toca `ecopunto.db`.

## Roles y permisos

- **CITIZEN:** registro público; consultar perfil, depósitos propios, saldo y transacciones; registrar depósitos propios. No puede elegir el ciudadano asociado a la solicitud ni asignarse un rol.
- **ADMIN:** gestionar materiales, EcoPuntos y compartimentos; ver alertas y recolecciones; resolver alertas; consultar depósitos y colecciones generales. La creación del primer administrador se protege mediante bootstrap de un solo uso.
- **RECYCLER:** consultar materiales, EcoPuntos, compartimentos y alertas; registrar recolecciones propias y consultar su historial. No puede consultar depósitos privados de ciudadanos.

Las rutas privadas requieren `Authorization: Bearer <access_token>`. El acceso token se obtiene con login.

## Endpoints principales

Todas las rutas de negocio usan el prefijo `/api/v1`.

| Método | Ruta | Acceso |
| --- | --- | --- |
| `POST` | `/auth/register` | Público; crea siempre CITIZEN |
| `POST` | `/auth/login` | Público |
| `POST` | `/auth/bootstrap-admin` | Token temporal configurado; una vez |
| `GET` | `/users/me` | Usuario autenticado |
| `POST` | `/users` | ADMIN (crear usuario y asignar rol) |
| `GET`, `POST` | `/materials` | Lectura autenticada; POST ADMIN |
| `PATCH` | `/materials/{id}` | ADMIN |
| `GET`, `POST` | `/ecopoints` | Lectura autenticada; POST ADMIN |
| `GET`, `PATCH` | `/ecopoints/{id}` | Lectura autenticada; PATCH ADMIN |
| `GET`, `POST` | `/ecopoints/{id}/compartments` | Lectura autenticada; POST ADMIN |
| `PATCH` | `/compartments/{id}` | ADMIN |
| `POST` | `/deposits` | CITIZEN autenticado |
| `GET` | `/deposits/me` | CITIZEN autenticado |
| `GET` | `/deposits/{id}` | Dueño o ADMIN |
| `GET` | `/points/balance`, `/points/transactions` | CITIZEN autenticado |
| `GET` | `/alerts` | ADMIN y RECYCLER |
| `PATCH` | `/alerts/{id}/resolve` | ADMIN y RECYCLER |
| `POST` | `/collections` | RECYCLER autenticado |
| `GET` | `/collections` | ADMIN (todas) o RECYCLER (propias) |
| `GET` | `/collections/{id}` | ADMIN o reciclador responsable |

`PATCH /alerts/{id}/resolve` es para resolución operativa manual. Una recolección completada también resuelve alertas activas del compartimento cuando el nivel vuelve a estar bajo el umbral.

## Ejemplos

Registrar y autenticar un ciudadano:

```powershell
$register = @{ email = 'persona@ejemplo.com'; full_name = 'Persona Ejemplo'; password = 'UnaClavePropiaLarga123!' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/register -ContentType 'application/json' -Body $register
$login = @{ email = 'persona@ejemplo.com'; password = 'UnaClavePropiaLarga123!' } | ConvertTo-Json
$token = (Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/login -ContentType 'application/json' -Body $login).access_token
$headers = @{ Authorization = "Bearer $token" }
```

Después de `python -m app.seed`, obtener EcoPuntos y compartimentos:

```powershell
$points = Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/ecopoints -Headers $headers
$point = $points | Select-Object -First 1
$compartments = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/ecopoints/$($point.id)/compartments" -Headers $headers
$materials = Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/materials -Headers $headers
```

El depósito requiere los UUID obtenidos en los pasos previos. El servidor deriva `citizen_id` del token:

```powershell
$pet = $materials | Where-Object name -eq 'PET'
$compartment = $compartments | Where-Object material_id -eq $pet.id
$deposit = @{ ecopoint_id = $point.id; compartment_id = $compartment.id; material_id = $pet.id; weight_g = 100 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/deposits -Headers $headers -ContentType 'application/json' -Body $deposit
```

La respuesta incluye el factor histórico, peso, EcoPuntos otorgados y fecha UTC. Con PET a 0.25, 100 g generan `25.0000` puntos.

## Reglas y supuestos

- Los puntos se calculan en el servicio de negocio: `peso_g × factor_puntos_por_gramo`.
- Los puntos se guardan con cuatro decimales y redondeo `ROUND_HALF_UP` a cuatro posiciones. El factor aplicado queda copiado en cada depósito.
- El saldo es la suma de transacciones; no se guarda un saldo paralelo. Los depósitos generan una transacción EARN. El modelo admite REDEEM negativo para una futura etapa, sin endpoint de redención en esta versión.
- Depósito, actualización del compartimento, transacción y eventual alerta se confirman juntos. Colección y actualización del compartimento y alerta también son atómicas.
- No se acepta un depósito que exceda la capacidad del compartimento, use un material no coincidente o vaya a un punto/compartimento inactivo.
- Los `POST /collections` registran una recolección como COMPLETED y reducen el peso disponible en el compartimento de forma inmediata. No se implementa un flujo de programación.
- SQLite no requiere migraciones para este prototipo; `create_all` solo crea tablas faltantes y no altera tablas existentes.

## Limitaciones

No hay frontend conectado, clasificación por IA, sensores, carga de imágenes, gestión de catálogo de beneficios, redenciones ni flujo de programación de recolecciones. La gestión de usuarios se limita a creación; edición, listado y desactivación administrativa quedan pendientes. Para cambios de esquema futuros se recomienda incorporar migraciones con Alembic antes de evolucionar una base con datos.

# Backend EcoPunto

API REST de EcoPunto, construida con FastAPI, SQLAlchemy, Pydantic y SQLite. Esta guía describe el componente backend; la instalación del proyecto completo está en el [README principal](../README.md).

## Requisitos y dependencias

Python 3.11 o posterior. Las dependencias con sus rangos compatibles están declaradas en `requirements.txt`: FastAPI, Uvicorn, SQLAlchemy, Pydantic Settings, python-dotenv, PyJWT, pwdlib con Argon2, email-validator, pytest e httpx.

Desde `backend/`, instala en un entorno virtual:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Si no se dispone de `py`, usa `python -m venv .venv` después de instalar Python. Si PowerShell impide activar el entorno, usa `\.venv\Scripts\python.exe -m ...`.

## Configuración

Usa `.env.example` como referencia y crea `backend/.env` localmente. No versionar ni compartir este archivo. Variables reconocidas por la configuración:

| Variable | Propósito | Predeterminado o validación |
| --- | --- | --- |
| `DATABASE_URL` | Conexión SQLAlchemy | `sqlite:///./ecopunto.db` |
| `JWT_SECRET_KEY` | Clave para firmar tokens | Si se configura debe tener al menos 32 caracteres; sin ella se usa una clave efímera por proceso |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Vigencia del token | 30 minutos; rango permitido 1–1440 |
| `CORS_ORIGINS` | Lista JSON de orígenes permitidos | localhost y 127.0.0.1 en puerto 5173 |
| `BOOTSTRAP_ADMIN_TOKEN` | Habilitación del primer ADMIN | Opcional; debe tener al menos 32 caracteres para habilitar la ruta |

Configura una `JWT_SECRET_KEY` privada y estable en desarrollo compartido para que reiniciar Uvicorn no invalide los tokens. Cada integrante debe generar sus propios valores secretos.

## Base de datos y seed

Al iniciar la aplicación, SQLAlchemy `create_all` crea tablas que falten; no aplica migraciones a tablas ya existentes. SQLite usa por defecto `./ecopunto.db` relativo al directorio de trabajo. Ejecuta el seed desde `backend/` si necesitas datos de catálogo:

```powershell
python -m app.seed
```

El seed crea de forma idempotente Aluminio (0.50 puntos/g), PET (0.25 puntos/g), un EcoPunto y sus compartimentos. No crea usuarios ni credenciales.

## Crear el primer ADMIN

`POST /api/v1/auth/bootstrap-admin` requiere `BOOTSTRAP_ADMIN_TOKEN` y el encabezado `X-Bootstrap-Token`. Solo crea el primer administrador cuando todavía no existe uno. Un valor ausente o inválido produce 404; si ya hay ADMIN, devuelve 409. Consulta el procedimiento seguro en [README principal — cuentas y roles](../README.md#cuentas-y-roles). No se mantienen credenciales predeterminadas.

Los ciudadanos se registran públicamente con `POST /auth/register`; ese endpoint siempre asigna CITIZEN. Un ADMIN puede crear cuentas mediante `POST /users`; el backend recibe rol, correo, nombre y contraseña y aplica autenticación por rol.

## Ejecutar el servidor y comprobar salud

Desde `backend/` con el entorno virtual activo:

```powershell
python -m uvicorn app.main:app --reload
```

- API: `http://127.0.0.1:8000`
- Swagger/OpenAPI: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## Rutas y permisos

Las rutas siguientes se agregan bajo `/api/v1`. Toda ruta privada requiere `Authorization: Bearer <access_token>`.

| Método | Ruta | Acceso |
| --- | --- | --- |
| `POST` | `/auth/register` | Público; crea CITIZEN |
| `POST` | `/auth/login` | Público; devuelve access token Bearer |
| `POST` | `/auth/bootstrap-admin` | Encabezado temporal; primer ADMIN solamente |
| `GET` | `/users/me` | Cualquier usuario autenticado |
| `POST` | `/users` | ADMIN; provisiona una cuenta con rol especificado |
| `GET` | `/materials` | Cualquier usuario autenticado; ADMIN también recibe inactivos |
| `POST`, `PATCH` | `/materials`, `/materials/{id}` | ADMIN |
| `GET` | `/ecopoints`, `/ecopoints/{id}` | Cualquier usuario autenticado; ADMIN puede consultar inactivos |
| `POST`, `PATCH` | `/ecopoints`, `/ecopoints/{id}` | ADMIN |
| `GET` | `/ecopoints/{id}/compartments` | Cualquier usuario autenticado; ADMIN también recibe inactivos |
| `POST` | `/ecopoints/{id}/compartments` | ADMIN |
| `PATCH` | `/compartments/{id}` | ADMIN |
| `POST` | `/deposits` | CITIZEN; el propietario se deriva del JWT |
| `GET` | `/deposits/me` | CITIZEN; depósitos propios |
| `GET` | `/deposits/{id}` | Dueño del depósito o ADMIN |
| `GET` | `/points/balance`, `/points/transactions` | CITIZEN |
| `GET` | `/alerts` | ADMIN y RECYCLER |
| `PATCH` | `/alerts/{id}/resolve` | ADMIN y RECYCLER |
| `POST` | `/collections` | RECYCLER |
| `GET` | `/collections` | ADMIN: todas; RECYCLER: propias |
| `GET` | `/collections/{id}` | ADMIN o reciclador responsable |

No existe un endpoint `GET /deposits` para listar depósitos de todos los ciudadanos. ADMIN solo puede consultar un depósito individual si conoce su ID. Tampoco existen endpoints de beneficios/redenciones ni de métricas agregadas.

## Reglas de negocio principales

- El ciudadano envía EcoPunto, material, compartimento y peso en gramos. El backend asocia el ciudadano desde JWT.
- `weight_g` debe ser entero positivo y no superar 100.000 g.
- El compartimento debe pertenecer al EcoPunto y al material indicados; el depósito no puede superar la capacidad disponible.
- Los puntos se calculan con el factor vigente del material, redondeados a cuatro decimales. El factor aplicado queda asociado al depósito.
- Depósito, actualización del compartimento, transacción de puntos y eventual alerta se confirman en una transacción de base de datos.
- `POST /collections` registra una recolección como `COMPLETED`, reduce el peso y resuelve alertas activas cuando el nivel cae por debajo del umbral. No hay programación de rutas.
- La resolución manual de una alerta usa `PATCH /alerts/{id}/resolve`.

## Pruebas

Desde `backend/`:

```powershell
python -m pytest -q
```

Las pruebas sustituyen la conexión por SQLite en memoria mediante `StaticPool`; no utilizan el archivo de base de datos local.

## Límites actuales

El frontend conecta autenticación, operaciones ciudadanas de depósito/puntos y gestión administrativa de catálogo. La interfaz de alertas y recolecciones para ADMIN/RECYCLER aún está pendiente. También faltan beneficios/redenciones y métricas agregadas. No hay sensores, cámaras, IA de clasificación ni integración con hardware.

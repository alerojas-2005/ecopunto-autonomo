# Backend EcoPunto

API REST del proyecto **EcoPunto Autónomo**, desarrollada con FastAPI. Este componente administra la autenticación, los usuarios, los EcoPuntos, los materiales, los depósitos, los EcoPuntos acumulados, las alertas y las recolecciones.

La guía general del proyecto, incluida la instalación completa y las modalidades de conexión a bases de datos, se encuentra en el [README principal](../README.md).

## 1. Tecnologías

- Python 3.11 o superior.
- FastAPI.
- Uvicorn.
- SQLAlchemy.
- Pydantic y Pydantic Settings.
- SQLite para instalaciones independientes.
- PostgreSQL para entornos compartidos.
- PyJWT para autenticación mediante tokens.
- Argon2 para el almacenamiento seguro de contraseñas.
- Pytest para pruebas.

Las dependencias y sus versiones compatibles se encuentran en `requirements.txt`.

## 2. Requisitos previos

Antes de ejecutar el backend, verifica que tengas instalado:

- Python 3.11 o superior.
- pip.
- Git.

## 3. Instalación

Desde la raíz del proyecto, ingresa a la carpeta del backend:

```powershell
cd backend
```

Crea un entorno virtual:

```powershell
py -3.11 -m venv .venv
```

Actívalo:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instala las dependencias:

```powershell
python -m pip install -r requirements.txt
```

Si el comando `py -3.11` no está disponible, puedes utilizar:

```powershell
python -m venv .venv
```

## 4. Configuración del entorno

Crea el archivo `.env` a partir de la plantilla:

```powershell
Copy-Item .env.example .env
```

El archivo `.env` contiene la configuración local del backend. No debe subirse al repositorio ni compartirse públicamente.

Las principales variables son:

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | Dirección de conexión a la base de datos. |
| `JWT_SECRET_KEY` | Clave privada para firmar los tokens de autenticación. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Tiempo de vigencia de los tokens. |
| `CORS_ORIGINS` | Orígenes autorizados para consumir la API. |
| `BOOTSTRAP_ADMIN_TOKEN` | Token temporal para crear el primer administrador. |

### Base de datos

El backend utiliza SQLite por defecto:

```env
DATABASE_URL=sqlite:///./ecopunto.db
```

Para conectar el backend a PostgreSQL en Supabase, configura `DATABASE_URL` con la cadena de conexión correspondiente al proyecto autorizado.

No publiques credenciales, contraseñas ni claves privadas.

### Seguridad

Configura una `JWT_SECRET_KEY` privada y estable. Debe tener al menos 32 caracteres.

En entornos compartidos, los integrantes autorizados deben utilizar la configuración de conexión y los valores secretos establecidos para el proyecto.

## 5. Inicialización de la base de datos

Al iniciar la aplicación, SQLAlchemy crea las tablas que no existan mediante `create_all`.

Este procedimiento no modifica automáticamente las tablas existentes ni reemplaza un sistema de migraciones de esquema.

Para cargar los datos iniciales del catálogo en una instalación independiente, ejecuta desde `backend/`:

```powershell
python -m app.seed
```

El seed incorpora:

- Material Aluminio.
- Material PET.
- Factores iniciales de asignación de puntos.
- Un EcoPunto de ejemplo.
- Sus compartimentos.

El seed no crea usuarios ni contraseñas.

**Importante:** no ejecutes el seed sobre la base de datos compartida de Supabase sin autorización.

## 6. Crear el primer administrador

El primer usuario ADMIN se crea mediante:

```http
POST /api/v1/auth/bootstrap-admin
```

Este procedimiento requiere configurar `BOOTSTRAP_ADMIN_TOKEN` y enviar el encabezado:

```http
X-Bootstrap-Token: valor_configurado
```

La ruta solamente permite crear el primer administrador cuando todavía no existe uno.

Después de realizar el proceso, deshabilita el token temporal.

Los ciudadanos pueden registrarse mediante el endpoint público de registro. El registro público asigna exclusivamente el rol `CITIZEN`.

Los usuarios con rol ADMIN pueden crear otras cuentas mediante el endpoint de gestión de usuarios.

## 7. Ejecución del servidor

Desde la carpeta `backend/`, con el entorno virtual activo:

```powershell
python -m uvicorn app.main:app --reload
```

El servidor estará disponible en:

- API: http://127.0.0.1:8000
- Documentación Swagger: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

Swagger permite consultar los endpoints, sus parámetros, los modelos de datos y los requisitos de autenticación.

## 8. Endpoints principales

Todos los endpoints se encuentran bajo el prefijo `/api/v1`.

| Módulo | Endpoint | Funcionalidad |
|---|---|---|
| Autenticación | `POST /auth/register` | Registro de ciudadanos. |
| Autenticación | `POST /auth/login` | Inicio de sesión. |
| Autenticación | `POST /auth/bootstrap-admin` | Creación del primer administrador. |
| Usuarios | `GET /users/me` | Consulta del perfil autenticado. |
| Usuarios | `POST /users` | Creación de usuarios por ADMIN. |
| Materiales | `/materials` | Consulta y administración de materiales. |
| EcoPuntos | `/ecopoints` | Consulta y administración de EcoPuntos. |
| Compartimentos | `/compartments` | Administración de compartimentos. |
| Depósitos | `POST /deposits` | Registro de depósitos ciudadanos. |
| Depósitos | `GET /deposits/me` | Consulta de depósitos propios. |
| Depósitos | `GET /deposits/{id}` | Consulta de un depósito individual con permisos. |
| Puntos | `/points/balance` | Consulta del saldo de puntos. |
| Puntos | `/points/transactions` | Consulta de transacciones. |
| Alertas | `/alerts` | Consulta de alertas. |
| Recolecciones | `/collections` | Registro y consulta de recolecciones. |

Las operaciones disponibles y sus permisos dependen del rol autenticado. Para consultar los métodos HTTP y parámetros específicos, utiliza Swagger.

No existe un endpoint general `GET /deposits` para listar todos los depósitos de los ciudadanos.

## 9. Reglas de negocio

- El ciudadano registra un depósito indicando EcoPunto, material, compartimento y peso en gramos.
- La identidad del ciudadano se obtiene del token de autenticación.
- El peso debe ser un entero positivo y no superar los 100.000 gramos.
- El compartimento debe pertenecer al EcoPunto y al material indicados.
- El depósito no puede superar la capacidad disponible del compartimento.
- Los puntos se calculan utilizando el factor vigente del material y se redondean a cuatro decimales.
- El factor aplicado queda asociado al depósito.
- El registro del depósito, la actualización del compartimento y la transacción de puntos se gestionan dentro de una transacción de base de datos.
- Las recolecciones registradas reducen el peso acumulado y pueden resolver alertas según el nivel del compartimento.

## 10. Pruebas

Para ejecutar las pruebas automatizadas, utiliza:

```powershell
python -m pytest -q
```

Las pruebas utilizan SQLite en memoria y no requieren modificar la base de datos local.

## 11. Limitaciones actuales

El backend todavía no dispone de funcionalidades para:

- Beneficios y redenciones de puntos.
- Métricas agregadas.
- Clasificación automática de residuos mediante inteligencia artificial.
- Integración con sensores, cámaras o hardware físico.
- Programación automática de rutas de recolección.

La simulación 3D representa visualmente el funcionamiento propuesto de EcoPunto, pero no implica una conexión real con dispositivos físicos.

## 12. Estructura general

```text
backend/
├── app/
│   ├── core/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── seed.py
│   └── main.py
├── docs/
├── scripts/
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

Para conocer la estructura completa y las instrucciones de ejecución del sistema, consulta el [README principal](../README.md).
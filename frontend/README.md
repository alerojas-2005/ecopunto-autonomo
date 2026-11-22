# Frontend EcoPunto

Cliente web de EcoPunto Autónomo creado con React, TypeScript y Vite. La guía de instalación completa, variables, roles, backend y trabajo colaborativo está en el [README principal](../README.md).

## Requisitos

- Node.js compatible con Vite 8: Node `^20.19.0` o `>=22.12.0`.
- npm.
- Backend ejecutándose en `http://127.0.0.1:8000` para usar las funciones conectadas.

Las dependencias exactas de proyecto se declaran en `package.json` y `package-lock.json`.

## Instalación local

Desde `frontend/`, crea `.env` solo si no existe y luego instala dependencias usando el lockfile:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
npm ci
```

`VITE_API_BASE_URL` define la URL base de la API. El valor local de ejemplo es `http://127.0.0.1:8000/api/v1`. `.env` es local y no debe subirse.

## Ejecutar y validar

```powershell
npm run dev
npm run lint
npm run build
```

Vite mostrará la dirección local del frontend, normalmente `http://localhost:5173`. Para el uso de frontend y backend en dos terminales, consulta la sección [Ejecución simultánea](../README.md#ejecutar-ambos-componentes).

## Estado funcional

El registro ciudadano consulta las universidades habilitadas y crea cuentas exclusivamente CITIZEN; el inicio de sesión y el perfil usan la API. CITIZEN consulta saldo, transacciones e historial propios y registra depósitos. ADMIN consulta resúmenes globales, gestiona EcoPuntos, materiales, compartimentos, usuarios y habilitación de universidades. ADMIN y RECYCLER consultan y resuelven alertas y revisan recolecciones; RECYCLER registra recolecciones dentro del ámbito que aplica el backend. Beneficios y redenciones siguen pendientes porque el backend no expone esos endpoints.

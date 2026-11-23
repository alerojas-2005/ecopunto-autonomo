# Frontend EcoPunto

Aplicación web de **EcoPunto Autónomo**, desarrollada con React, TypeScript y Vite. Permite a los usuarios interactuar con las funcionalidades del sistema mediante una interfaz gráfica e incluye una simulación virtual 3D del EcoPunto.

La guía general del proyecto, incluida la configuración del backend y las modalidades de conexión a bases de datos, se encuentra en el [README principal](../README.md).

## 1. Tecnologías

- React 19.
- TypeScript.
- Vite.
- Three.js para la simulación 3D.
- npm para la gestión de dependencias.
- ESLint para el análisis estático del código.

Las dependencias y versiones del proyecto se encuentran en `package.json` y `package-lock.json`.

## 2. Requisitos previos

Antes de ejecutar el frontend, verifica que tengas instalado:

- Node.js `^20.19.0` o `>=22.12.0`.
- npm.
- Git.

También debes tener disponible el backend para utilizar las funcionalidades que requieren conexión con la API.

## 3. Instalación

Desde la raíz del proyecto, ingresa a la carpeta del frontend:

```powershell
cd frontend
```

Crea el archivo de configuración local a partir de la plantilla:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Instala las dependencias utilizando el archivo de bloqueo:

```powershell
npm ci
```

## 4. Configuración del entorno

El frontend utiliza la variable `VITE_API_BASE_URL` para establecer la dirección base del backend.

En el archivo `frontend/.env` configura:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Si el backend se encuentra en otro servidor o entorno, utiliza la dirección correspondiente.

El archivo `.env` es local y no debe subirse al repositorio.

**Importante:** las variables que comienzan con `VITE_` pueden quedar expuestas en el código del navegador. No almacenes contraseñas, claves privadas ni secretos en ellas.

## 5. Ejecutar el frontend

Desde la carpeta `frontend/`, ejecuta:

```powershell
npm run dev
```

Vite iniciará el servidor de desarrollo y mostrará la dirección local de acceso.

Normalmente estará disponible en:

http://localhost:5173

Para utilizar las funcionalidades conectadas, el backend también debe estar ejecutándose.

## 6. Validación del proyecto

El frontend incluye comandos para revisar el código y generar la compilación de producción.

### Análisis de código

```powershell
npm run lint
```

### Compilación

```powershell
npm run build
```

La compilación genera los archivos de distribución en la carpeta `dist/`.

## 7. Funcionalidades de la interfaz

La aplicación presenta funcionalidades de acuerdo con el rol del usuario autenticado.

### CITIZEN

El ciudadano puede:

- Registrarse en la plataforma.
- Iniciar sesión.
- Consultar su perfil.
- Consultar su saldo de EcoPuntos.
- Consultar sus transacciones.
- Revisar su historial de depósitos.
- Registrar depósitos en los EcoPuntos disponibles.
- Acceder a la simulación virtual 3D.

### ADMIN

El administrador cuenta con funcionalidades de gestión del sistema, entre ellas:

- Consulta de información general.
- Gestión de universidades y usuarios.
- Gestión de materiales.
- Gestión de EcoPuntos y compartimentos.
- Consulta de información administrativa disponible.
- Acceso a la simulación virtual 3D.

Las operaciones administrativas están sujetas a los permisos y endpoints disponibles en el backend.

### RECYCLER

El reciclador dispone de funcionalidades relacionadas con la gestión de alertas y recolecciones, según los permisos definidos por el backend, y puede acceder a la simulación virtual 3D.

## 8. Simulación virtual 3D

El frontend incorpora una simulación 3D construida con Three.js.

Su propósito es representar visualmente el funcionamiento propuesto del EcoPunto Autónomo, incluyendo su estructura y la interacción simulada con los residuos.

La simulación es una representación virtual y no corresponde a una conexión física con sensores, básculas, cámaras, microcontroladores o dispositivos IoT.

La clasificación automática mediante inteligencia artificial y la integración con hardware físico no forman parte de las funcionalidades implementadas actualmente.

## 9. Conexión con el backend

El frontend consume la API REST del proyecto mediante la variable `VITE_API_BASE_URL`.

Para utilizar la aplicación completa, debes:

1. Configurar y ejecutar el backend.
2. Configurar la URL de la API en el archivo `.env` del frontend.
3. Ejecutar el servidor de desarrollo del frontend.
4. Acceder desde el navegador a la dirección indicada por Vite.

La autenticación utiliza tokens Bearer proporcionados por el backend para las operaciones protegidas.

## 10. Estructura general

```text
frontend/
├── public/
├── src/
│   ├── assets/
│   ├── components/
│   ├── pages/
│   ├── services/
│   ├── App.tsx
│   └── main.tsx
├── .env.example
├── index.html
├── package.json
├── package-lock.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

La estructura puede ampliarse a medida que se incorporen nuevas funcionalidades.

## 11. Solución de problemas

### El frontend no puede conectarse al backend

Verifica que:

- El backend esté ejecutándose.
- La variable `VITE_API_BASE_URL` tenga la dirección correcta.
- El backend permita el origen del frontend mediante `CORS_ORIGINS`.

### No se reconoce npm

Verifica la instalación de Node.js y npm:

```powershell
node -v
npm -v
```

### Hay errores al instalar dependencias

Comprueba que estás en la carpeta `frontend/` y vuelve a ejecutar:

```powershell
npm ci
```

### La compilación presenta errores

Ejecuta:

```powershell
npm run lint
npm run build
```

Revisa los mensajes de salida para identificar los archivos y componentes que requieren corrección.

## 12. Documentación adicional

Para conocer la arquitectura general, los roles, la configuración de bases de datos y la ejecución simultánea de los componentes, consulta el [README principal](../README.md).
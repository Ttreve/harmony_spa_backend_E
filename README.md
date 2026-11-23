# Harmony Spa – Backend

API REST del sistema Harmony Spa, construida con **FastAPI**, **SQLAlchemy 2** y **MySQL**, organizada por capas
(api → services → repositories → models).

## Requisitos

- Python 3.11 o superior
- MySQL 8 (con MySQL Workbench para crear la base de datos)

## Estructura del proyecto

```
harmony_spa_backend/
├── app/
│   ├── main.py                  # Fábrica de la aplicación (CORS, routers, errores)
│   ├── core/                    # config, seguridad (Argon2/JWT), permisos, excepciones
│   ├── api/                     # health, deps (usuario actual / roles) y v1 (auth, users)
│   ├── infrastructure/database/ # base, connection (engine) y session (get_db)
│   ├── domain/                  # enums (UserRole, AppointmentStatus), entities e interfaces
│   ├── models/                  # User, UserSession, perfiles, Procedure, Appointment (SQLAlchemy)
│   ├── schemas/                 # Esquemas Pydantic de entrada/salida
│   ├── repositories/            # Acceso a datos (sin lógica de negocio)
│   └── services/                # Lógica de negocio (AuthService, UserService)
├── migrations/                  # Alembic
├── scripts/create_super_admin.py # Crea el SUPER_ADMIN (python -m scripts.create_super_admin)
└── tests/                       # Pruebas con pytest (usan SQLite, no tocan MySQL)
```

## Cómo leer este proyecto (guía rápida)

Cada carpeta tiene una sola responsabilidad. Una petición HTTP recorre las capas en este orden:

```
Petición HTTP
   │
   ▼
app/api/v1/*.py          Endpoint: recibe el JSON, valida con schemas y llama al servicio.
   │   (app/api/deps.py  Dependencias: leen el token, obtienen el usuario y revisan el rol.)
   ▼
app/services/*.py        Reglas de negocio (AuthService, UserService).
   │   (app/core/*       Seguridad Argon2/JWT, permisos por rol, configuración, errores.)
   ▼
app/repositories/*.py    Consultas a la base de datos (sin reglas, sin commit).
   ▼
app/models/*.py          Tablas (users, user_sessions, perfiles, procedimientos, citas)  →  MySQL
```

**Dónde está cada cosa de la autenticación**

| Quiero entender… | Archivo |
|---|---|
| Cómo se protege una contraseña (Argon2id) y se crea/verifica un JWT | `app/core/security.py` |
| El flujo de login, logout y validación de sesión (2 h / 30 min) | `app/services/auth_service.py` |
| Cómo un endpoint exige sesión o un rol | `app/api/deps.py` |
| Los endpoints `/auth/login`, `/auth/logout`, `/auth/me` | `app/api/v1/auth.py` |
| Qué puede hacer cada rol | `app/core/permissions.py` y `app/api/v1/users.py` |
| Las tablas `users` y `user_sessions` | `app/models/user.py`, `app/models/user_session.py` |
| Perfiles, procedimientos y citas (ORM) | `app/models/client_profile.py`, `employee_profile.py`, `procedure.py`, `procedure_session.py`, `appointment.py` |
| Crear un usuario con su perfil según el rol | `app/schemas/user.py` (validación) y `app/services/user_service.py` |
| Cómo se crea el SUPER_ADMIN (único) | `scripts/create_super_admin.py` |
| Los tiempos y la clave del JWT | `app/core/config.py` y `.env` |

**Convenciones:** los errores de negocio se lanzan como `AppError` (`app/core/exceptions.py`) y salen como `{"detail": "..."}`;
las fechas se guardan en UTC sin zona horaria (`utc_now_naive`); los repositorios nunca hacen `commit`, lo hace el servicio.

## Puesta en marcha

1. **Crear la base de datos** en una instancia de MySQL con conexión (Workbench):

   ```sql
   CREATE DATABASE harmony_spa
   CHARACTER SET utf8mb4
   COLLATE utf8mb4_unicode_ci;
   ```

2. **Entorno virtual e instalación de dependencias**

   ```bash
   python -m venv .venv
   # Windows (PowerShell):  .venv\Scripts\Activate.ps1
   # Windows (cmd):         .venv\Scripts\activate.bat
   # Linux / macOS:         source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno**: copia `.env.example` a `.env` y ajusta los valores.

   ```bash
   cp .env.example .env      # en Windows: copy .env.example .env
   ```

   Qué debes cambiar como mínimo:

   - `DATABASE_URL`: usuario, contraseña y host de tu MySQL.
   - `SECRET_KEY`: genera una con
     `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
     La aplicación **no arranca** si queda el valor de ejemplo o tiene menos de 32 caracteres.

   | Variable | Descripción | Por defecto |
   |---|---|---|
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | Vida máxima absoluta del token/sesión | 120 (2 horas) |
   | `INACTIVITY_TIMEOUT_MINUTES` | Minutos sin actividad para cerrar la sesión | 30 |
   | `CORS_ORIGINS` | Orígenes del frontend, separados por coma | `http://localhost:5173,http://localhost:3000` |

4. **Crear las tablas** (migraciones de Alembic):

   ```bash
   alembic upgrade head
   ```

5. **Crear el SUPER_ADMIN** (solo puede existir uno):

   ```bash
   python -m scripts.create_super_admin
   ```

   El script pide nombres, apellidos, correo y contraseña (mínimo 12 caracteres; se escribe oculta y se confirma).

6. **Ejecutar el proyecto**

   ```bash
   uvicorn app.main:app --reload
   ```

   | Qué | URL |
   |---|---|
   | API | http://127.0.0.1:8000 |
   | Documentación (Swagger) | http://127.0.0.1:8000/docs |
   | Estado del servidor | http://127.0.0.1:8000/health |
   | Estado de la conexión con MySQL | http://127.0.0.1:8000/health/ready |

## Pruebas

```bash
pytest
```

Las pruebas crean una base SQLite temporal; nunca usan ni modifican la base MySQL.

## Autenticación

Flujo basado en **JWT + tabla `user_sessions`**:

1. `POST /api/v1/auth/login` valida credenciales, crea una sesión (con el `jti` del token) y devuelve el `access_token`.
2. El cliente envía `Authorization: Bearer <access_token>` en cada petición.
3. En cada petición el backend comprueba que la sesión siga **activa**, **no haya vencido**
   (`ACCESS_TOKEN_EXPIRE_MINUTES`) y **no supere la inactividad** (`INACTIVITY_TIMEOUT_MINUTES`); además actualiza
   `last_activity_at`.
4. `POST /api/v1/auth/logout` revoca la sesión actual: el token deja de servir aunque no haya expirado.
5. Al desactivar a un usuario o al cambiar su contraseña se cierran sus sesiones (en el cambio de contraseña se
   conserva la actual).

**Probar en Swagger:** ejecuta `POST /auth/login`, copia el `access_token`, pulsa **Authorize** (arriba a la
derecha) y pega solo el token. **En Postman:** pestaña *Authorization* → *Bearer Token*.

**Conectar con el frontend:** guarda el `access_token` tras el login y envíalo en el encabezado `Authorization`.
El login también devuelve `expires_in` e `inactivity_timeout` (en segundos) y los datos del usuario (`user`).
Ante un `401` el frontend debe llevar al usuario al login. Agrega el origen del frontend en `CORS_ORIGINS`.

## Roles y permisos

Roles: `SUPER_ADMIN`, `ADMIN`, `ESTETICISTA`, `CLIENTE` (definidos en `app/domain/enums/user_role.py`).

| Rol | Puede hacer en /users |
|---|---|
| `SUPER_ADMIN` | Crear ADMIN, ESTETICISTA y CLIENTE (con su perfil); listar, consultar, actualizar y activar/desactivar usuarios |
| `ADMIN`, `ESTETICISTA`, `CLIENTE` | Solo su propio perfil (`/users/me`) |

- La gestión de usuarios es **solo del SUPER_ADMIN** por ahora; los permisos delegados al ADMIN ("según autorización") se definirán más adelante (`app/core/permissions.py` queda preparado).
- El SUPER_ADMIN **no se crea, edita ni desactiva por la API**: solo con el script; además la base de datos garantiza que solo exista uno.
- El **rol no se cambia** con una edición ordinaria, y los usuarios **no se eliminan físicamente**: se desactivan.
- Un CLIENTE se crea con `client_profile`; un ADMIN o ESTETICISTA, con `employee_profile`. No se aceptan perfiles incompatibles con el rol.
- Al **desactivar** una cuenta se cierran todas sus sesiones abiertas.

## Endpoints (prefijo `/api/v1`)

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/auth/login` | Público | Iniciar sesión |
| POST | `/auth/logout` | Autenticado | Cerrar la sesión actual (204 No Content) |
| GET | `/auth/me` | Autenticado | Usuario de la sesión |
| GET | `/users/me` | Autenticado | Ver mi perfil |
| PATCH | `/users/me` | Autenticado | Editar nombre, apellido y teléfono |
| POST | `/users/me/password` | Autenticado | Cambiar mi contraseña |
| POST | `/users` | SUPER_ADMIN | Crear usuario con su perfil |
| GET | `/users` | SUPER_ADMIN | Listar (filtros `role`, `is_active`, `search`, `skip`, `limit`) |
| GET | `/users/{id}` | SUPER_ADMIN | Consultar un usuario |
| PATCH | `/users/{id}` | SUPER_ADMIN | Actualizar nombre, apellido, correo y teléfono |
| PATCH | `/users/{id}/status` | SUPER_ADMIN | Activar o desactivar (`{"is_active": false}`) |

Política de contraseñas: mínimo 12 caracteres, al menos una letra y un número, máximo 128 caracteres. Se guardan como hash **Argon2id** (`pwdlib`); nunca la contraseña original.

## Migraciones

```bash
alembic revision --autogenerate -m "descripcion del cambio"   # generar
alembic upgrade head                                          # aplicar
alembic downgrade -1                                          # deshacer la última
```

## Problemas comunes

- **`SECRET_KEY debe tener al menos 32 caracteres...`**: falta definir `SECRET_KEY` en `.env`.
- **No puedo iniciar sesión con un usuario creado antes de usar Argon2**: ese usuario tiene un hash de otro algoritmo (bcrypt). En desarrollo, bórralo en MySQL (`DELETE FROM users;`) y vuelve a crearlo con `python -m scripts.create_super_admin`.
- **`/health/ready` responde 503**: revisa `DATABASE_URL` y que la instancia de MySQL esté activa.
- **`Table 'users' doesn't exist`**: falta ejecutar `alembic upgrade head`.
- **Error de CORS en el navegador**: agrega el origen exacto del frontend a `CORS_ORIGINS` y reinicia el servidor.

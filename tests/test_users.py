"""Pruebas del módulo de gestión de usuarios (/api/v1/users).

Reglas que se comprueban:
  - Solo el SUPER_ADMIN gestiona usuarios (ADMIN, ESTETICISTA y CLIENTE no).
  - Cada rol se crea con su perfil (cliente o empleado) y se rechazan los incompatibles.
  - No se crea otro SUPER_ADMIN ni se modifica el existente.
  - El rol no cambia con una edición ordinaria.
  - Desactivar una cuenta cierra sus sesiones y bloquea el login.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.domain.enums.user_role import UserRole
from app.infrastructure.database.session import SessionLocal
from app.models import ClientProfile, EmployeeProfile, User
from app.services import UserService
from tests.conftest import PASSWORD

USERS = "/api/v1/users"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/users/me"


# --- Datos de ejemplo -------------------------------------------------------
def _client_payload(**overrides):
    payload = {
        "first_name": "Maria",
        "last_name": "Rodriguez",
        "email": "maria@harmonyspa.co",
        "phone": "3101234567",
        "password": "MariaCliente2026Segura",
        "role": "CLIENTE",
        "client_profile": {
            "birth_date": "1990-05-15",
            "address": "Bogota",
            "emergency_contact_name": "Ana Rodriguez",
            "emergency_contact_phone": "3111234567",
            "notes": "Cliente nueva",
        },
    }
    payload.update(overrides)
    return payload


def _employee_payload(**overrides):
    payload = {
        "first_name": "Laura",
        "last_name": "Gomez",
        "email": "laura@harmonyspa.co",
        "phone": "3001234567",
        "password": "LauraSpa2026Segura",
        "role": "ESTETICISTA",
        "employee_profile": {
            "job_title": "Esteticista",
            "specialty": "Tratamientos faciales",
            "hire_date": "2026-11-22",
            "is_available": True,
            "notes": "Personal de atención",
        },
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def root_headers(make_user, login, auth):
    """Encabezados de un SUPER_ADMIN ya autenticado."""
    make_user(UserRole.SUPER_ADMIN, email="root@harmonyspa.co")
    return auth(login("root@harmonyspa.co"))


# --- Permisos: solo SUPER_ADMIN ---------------------------------------------
def test_users_endpoints_require_authentication(client):
    assert client.get(USERS).status_code == 401
    assert client.post(USERS, json=_client_payload()).status_code == 401


@pytest.mark.parametrize(
    "role", [UserRole.ADMIN, UserRole.ESTETICISTA, UserRole.CLIENTE]
)
def test_only_super_admin_can_manage_users(client, make_user, login, auth, role):
    make_user(role, email="otro@harmonyspa.co")
    target = make_user(UserRole.CLIENTE, email="objetivo@harmonyspa.co")
    headers = auth(login("otro@harmonyspa.co"))

    assert client.post(USERS, json=_client_payload(), headers=headers).status_code == 403
    assert client.get(USERS, headers=headers).status_code == 403
    assert client.get(f"{USERS}/{target.id}", headers=headers).status_code == 403
    assert (
        client.patch(f"{USERS}/{target.id}", json={"first_name": "Xx"}, headers=headers).status_code
        == 403
    )
    assert (
        client.patch(
            f"{USERS}/{target.id}/status", json={"is_active": False}, headers=headers
        ).status_code
        == 403
    )


# --- Crear usuarios con su perfil -------------------------------------------
def test_super_admin_creates_client_with_profile(client, root_headers):
    response = client.post(USERS, json=_client_payload(), headers=root_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "CLIENTE"
    assert body["email"] == "maria@harmonyspa.co"
    assert "password" not in body and "password_hash" not in body

    with SessionLocal() as db:
        profile = db.execute(
            select(ClientProfile).where(ClientProfile.user_id == body["id"])
        ).scalar_one()
        assert profile.address == "Bogota"
        assert profile.emergency_contact_name == "Ana Rodriguez"
        user = db.get(User, body["id"])
        # La contraseña quedó protegida con Argon2id.
        assert user.password_hash.startswith("$argon2id$")


@pytest.mark.parametrize("role", ["ESTETICISTA", "ADMIN"])
def test_super_admin_creates_employee_with_profile(client, root_headers, role):
    response = client.post(
        USERS, json=_employee_payload(role=role), headers=root_headers
    )

    assert response.status_code == 201
    user_id = response.json()["id"]
    with SessionLocal() as db:
        profile = db.execute(
            select(EmployeeProfile).where(EmployeeProfile.user_id == user_id)
        ).scalar_one()
        assert profile.job_title == "Esteticista"
        assert profile.is_available is True


def test_nobody_can_create_super_admin_through_api(client, root_headers):
    response = client.post(
        USERS,
        json=_employee_payload(role="SUPER_ADMIN"),
        headers=root_headers,
    )

    assert response.status_code == 422


def test_role_requires_its_own_profile(client, root_headers):
    # Cliente sin perfil de cliente.
    no_profile = _client_payload()
    del no_profile["client_profile"]
    # Empleado sin perfil de empleado.
    employee_no_profile = _employee_payload()
    del employee_no_profile["employee_profile"]
    # Perfiles incompatibles con el rol.
    client_with_employee = _client_payload(
        employee_profile=_employee_payload()["employee_profile"]
    )
    employee_with_client = _employee_payload(
        client_profile=_client_payload()["client_profile"]
    )

    for payload in (no_profile, employee_no_profile, client_with_employee, employee_with_client):
        assert client.post(USERS, json=payload, headers=root_headers).status_code == 422


def test_duplicate_email_returns_409(client, root_headers):
    first = client.post(USERS, json=_client_payload(), headers=root_headers)
    second = client.post(
        USERS, json=_client_payload(email="MARIA@harmonyspa.co"), headers=root_headers
    )

    assert first.status_code == 201
    assert second.status_code == 409


@pytest.mark.parametrize("password", ["12345678", "corta1", "SoloLetrasSinNumeros"])
def test_weak_password_returns_422(client, root_headers, password):
    response = client.post(
        USERS, json=_client_payload(password=password), headers=root_headers
    )

    assert response.status_code == 422


# --- Listado y consulta -----------------------------------------------------
def test_list_users_with_filters(client, make_user, root_headers):
    make_user(UserRole.CLIENTE, email="ana@harmonyspa.co")
    make_user(UserRole.CLIENTE, email="beto@harmonyspa.co", is_active=False)
    make_user(UserRole.ESTETICISTA, email="eva@harmonyspa.co")

    everyone = client.get(USERS, headers=root_headers).json()
    clientes = client.get(USERS, params={"role": "CLIENTE"}, headers=root_headers).json()
    activos = client.get(
        USERS, params={"role": "CLIENTE", "is_active": True}, headers=root_headers
    ).json()
    buscados = client.get(USERS, params={"search": "eva"}, headers=root_headers).json()
    paginado = client.get(USERS, params={"limit": 2}, headers=root_headers).json()

    assert everyone["total"] == 4  # incluye al SUPER_ADMIN
    assert clientes["total"] == 2
    assert activos["total"] == 1
    assert [u["email"] for u in buscados["items"]] == ["eva@harmonyspa.co"]
    assert len(paginado["items"]) == 2 and paginado["total"] == 4


def test_get_user_by_id_and_404(client, make_user, root_headers):
    target = make_user(UserRole.CLIENTE, email="ana@harmonyspa.co")

    ok = client.get(f"{USERS}/{target.id}", headers=root_headers)

    assert ok.json()["email"] == "ana@harmonyspa.co"
    assert client.get(f"{USERS}/99999", headers=root_headers).status_code == 404


# --- Actualización ------------------------------------------------------------
def test_update_user_data(client, make_user, root_headers):
    target = make_user(UserRole.CLIENTE, email="ana@harmonyspa.co")

    response = client.patch(
        f"{USERS}/{target.id}",
        json={"first_name": "  Ana María ", "email": "ANA.NUEVA@harmonyspa.co", "phone": None},
        headers=root_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["first_name"] == "Ana María"
    assert body["email"] == "ana.nueva@harmonyspa.co"
    assert body["phone"] is None


def test_update_cannot_change_role_or_status(client, make_user, root_headers):
    target = make_user(UserRole.CLIENTE, email="ana@harmonyspa.co")

    # "role" e "is_active" no existen en UserUpdate: se ignoran.
    response = client.patch(
        f"{USERS}/{target.id}",
        json={"first_name": "Ana", "role": "ADMIN", "is_active": False},
        headers=root_headers,
    )

    assert response.status_code == 200
    assert response.json()["role"] == "CLIENTE"
    assert response.json()["is_active"] is True


def test_update_duplicate_email_returns_409(client, make_user, root_headers):
    make_user(UserRole.CLIENTE, email="ana@harmonyspa.co")
    target = make_user(UserRole.CLIENTE, email="beto@harmonyspa.co")

    response = client.patch(
        f"{USERS}/{target.id}", json={"email": "ana@harmonyspa.co"}, headers=root_headers
    )

    assert response.status_code == 409


def test_update_rejects_null_for_required_fields(client, make_user, root_headers):
    target = make_user(UserRole.CLIENTE, email="ana@harmonyspa.co")

    for field in ("first_name", "last_name", "email"):
        response = client.patch(
            f"{USERS}/{target.id}", json={field: None}, headers=root_headers
        )
        assert response.status_code == 422


def test_super_admin_cannot_be_modified_through_api(client, make_user, login, auth):
    root = make_user(UserRole.SUPER_ADMIN, email="root@harmonyspa.co")
    headers = auth(login("root@harmonyspa.co"))

    assert (
        client.patch(f"{USERS}/{root.id}", json={"first_name": "Xx"}, headers=headers).status_code
        == 400
    )
    assert (
        client.patch(
            f"{USERS}/{root.id}/status", json={"is_active": False}, headers=headers
        ).status_code
        == 400
    )


# --- Activar / desactivar -----------------------------------------------------
def test_deactivating_user_kills_sessions_and_blocks_login(
    client, make_user, root_headers, login, auth
):
    target = make_user(UserRole.CLIENTE, email="ana@harmonyspa.co")
    target_token = login("ana@harmonyspa.co")

    response = client.patch(
        f"{USERS}/{target.id}/status", json={"is_active": False}, headers=root_headers
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    # La sesión abierta ya no sirve y no se puede iniciar otra.
    assert client.get(ME, headers=auth(target_token)).status_code == 401
    assert (
        client.post(LOGIN, json={"email": "ana@harmonyspa.co", "password": PASSWORD}).status_code
        == 403
    )


def test_reactivating_user_allows_new_login(client, make_user, root_headers):
    target = make_user(UserRole.CLIENTE, email="ana@harmonyspa.co", is_active=False)

    response = client.patch(
        f"{USERS}/{target.id}/status", json={"is_active": True}, headers=root_headers
    )

    assert response.status_code == 200
    assert (
        client.post(LOGIN, json={"email": "ana@harmonyspa.co", "password": PASSWORD}).status_code
        == 200
    )


def test_status_404_for_unknown_user(client, root_headers):
    response = client.patch(
        f"{USERS}/99999/status", json={"is_active": False}, headers=root_headers
    )

    assert response.status_code == 404


def test_users_are_never_deleted_physically(client, make_user, root_headers):
    target = make_user(UserRole.CLIENTE, email="ana@harmonyspa.co")

    # No existe DELETE /users/{id}.
    assert client.delete(f"{USERS}/{target.id}", headers=root_headers).status_code == 405


# --- Perfil propio ------------------------------------------------------------
def test_update_my_profile_cannot_change_role(client, make_user, login, auth):
    make_user(UserRole.CLIENTE, email="ana@harmonyspa.co")
    headers = auth(login("ana@harmonyspa.co"))

    response = client.patch(
        ME, json={"first_name": "Ana", "role": "ADMIN"}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Ana"
    assert response.json()["role"] == "CLIENTE"


def test_change_password_flow(client, make_user, login, auth):
    make_user(UserRole.CLIENTE, email="ana@harmonyspa.co")
    token_current = login("ana@harmonyspa.co")
    token_other = login("ana@harmonyspa.co")
    headers = auth(token_current)

    wrong = client.post(
        f"{ME}/password",
        json={"current_password": "Incorrecta1", "new_password": "NuevaClave2026"},
        headers=headers,
    )
    same = client.post(
        f"{ME}/password",
        json={"current_password": PASSWORD, "new_password": PASSWORD},
        headers=headers,
    )
    ok = client.post(
        f"{ME}/password",
        json={"current_password": PASSWORD, "new_password": "NuevaClave2026"},
        headers=headers,
    )

    assert wrong.status_code == 400
    assert same.status_code == 400
    assert ok.status_code == 200
    # La sesión actual sigue activa; las demás se cierran.
    assert client.get(ME, headers=auth(token_current)).status_code == 200
    assert client.get(ME, headers=auth(token_other)).status_code == 401
    # La contraseña anterior ya no sirve.
    assert (
        client.post(LOGIN, json={"email": "ana@harmonyspa.co", "password": PASSWORD}).status_code
        == 401
    )
    assert (
        client.post(
            LOGIN, json={"email": "ana@harmonyspa.co", "password": "NuevaClave2026"}
        ).status_code
        == 200
    )


# --- SUPER_ADMIN único --------------------------------------------------------
def test_create_super_admin_service_only_once():
    from app.core.exceptions import ConflictError

    with SessionLocal() as db:
        user = UserService(db).create_super_admin(
            first_name="Super",
            last_name="Admin",
            email="root@harmonyspa.co",
            password=PASSWORD,
        )
        assert user.role == UserRole.SUPER_ADMIN

    with SessionLocal() as db:
        with pytest.raises(ConflictError):
            UserService(db).create_super_admin(
                first_name="Otro",
                last_name="Admin",
                email="otro@harmonyspa.co",
                password=PASSWORD,
            )


def test_database_allows_only_one_super_admin():
    def _insert(email: str) -> None:
        with SessionLocal() as db:
            db.add(
                User(
                    first_name="S",
                    last_name="A",
                    email=email,
                    password_hash=hash_password(PASSWORD),
                    role=UserRole.SUPER_ADMIN,
                    is_active=True,
                )
            )
            db.commit()

    _insert("uno@harmonyspa.co")
    with pytest.raises(IntegrityError):
        _insert("dos@harmonyspa.co")

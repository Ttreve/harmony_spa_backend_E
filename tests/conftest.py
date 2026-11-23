"""Configuración de pruebas.

Las pruebas usan una base SQLite temporal, NUNCA la base MySQL del proyecto.
Las variables de entorno se fijan antes de importar la aplicación, y tienen
prioridad sobre el archivo .env.
"""

import os
import tempfile
from pathlib import Path

_TMP_DIR = tempfile.mkdtemp(prefix="harmony_spa_tests_")
os.environ["DATABASE_URL"] = (
    f"sqlite:///{Path(_TMP_DIR, 'test.db').as_posix()}?check_same_thread=false"
)
os.environ["SECRET_KEY"] = "clave-secreta-solo-para-pruebas-0123456789abcdef"
os.environ["APP_ENV"] = "testing"
os.environ["DEBUG"] = "false"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "120"
os.environ["INACTIVITY_TIMEOUT_MINUTES"] = "30"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.domain.enums.user_role import UserRole  # noqa: E402
from app.infrastructure.database.base import Base  # noqa: E402
from app.infrastructure.database.connection import engine  # noqa: E402
from app.infrastructure.database.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402

# Cumple la política: 12+ caracteres, con letras y números.
PASSWORD = "ClaveSegura2026"


@pytest.fixture(autouse=True)
def database():
    # Seguro extra: jamás borrar tablas de una base que no sea SQLite.
    assert engine.url.get_backend_name() == "sqlite", (
        "Las pruebas solo pueden ejecutarse contra SQLite"
    )
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def make_user():
    counter = {"n": 0}

    def _make_user(
        role: UserRole = UserRole.CLIENTE,
        *,
        email: str | None = None,
        password: str = PASSWORD,
        is_active: bool = True,
    ) -> User:
        counter["n"] += 1
        with SessionLocal() as db:
            user = User(
                first_name="Nombre",
                last_name="Apellido",
                email=email or f"{role.value.lower()}{counter['n']}@harmonyspa.co",
                password_hash=hash_password(password),
                role=role,
                is_active=is_active,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

    return _make_user


@pytest.fixture
def login(client):
    def _login(email: str, password: str = PASSWORD) -> str:
        response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    return _login


@pytest.fixture
def auth():
    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    return _auth

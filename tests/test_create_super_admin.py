"""Pruebas del script scripts/create_super_admin.py.

Se simulan las respuestas de la consola (input y getpass) y se comprueba el
resultado en la base SQLite de pruebas (nunca MySQL).
"""

from sqlalchemy import select

from app.domain.enums.user_role import UserRole
from app.infrastructure.database.session import SessionLocal
from app.models import User
from scripts import create_super_admin as script
from tests.conftest import PASSWORD


def _simulate_console(monkeypatch, *, email: str = "ISA@GMAIL.COM") -> None:
    """Simula que la persona escribe nombres, apellidos, correo y contraseña."""
    answers = iter(["Isaura", "Suarez", email])
    monkeypatch.setattr("sys.argv", ["create_super_admin"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    monkeypatch.setattr("getpass.getpass", lambda _prompt="": PASSWORD)


def test_script_creates_super_admin_with_argon2(monkeypatch, capsys):
    _simulate_console(monkeypatch)

    assert script.main() == 0
    assert "SUPER_ADMIN creado correctamente" in capsys.readouterr().out

    with SessionLocal() as db:
        admin = db.execute(select(User)).scalar_one()

    assert admin.role == UserRole.SUPER_ADMIN
    assert admin.email == "isa@gmail.com"  # el correo se guarda en minúsculas
    assert admin.password_hash.startswith("$argon2id$")  # nunca la clave original


def test_script_refuses_second_super_admin(monkeypatch, capsys):
    _simulate_console(monkeypatch)
    assert script.main() == 0

    _simulate_console(monkeypatch, email="otra@gmail.com")
    assert script.main() == 1
    assert "[ERROR]" in capsys.readouterr().out

    with SessionLocal() as db:
        assert len(db.execute(select(User)).scalars().all()) == 1

"""Crea el único usuario SUPER_ADMIN de Harmony Spa.

Este script se ejecuta desde la terminal local. NO existe un endpoint público
para crear este usuario (por seguridad). Solo puede existir UN SUPER_ADMIN.

Requisitos: entorno virtual activo, .env configurado y la base de datos
migrada (`alembic upgrade head`).

Ejecútalo desde la raíz del proyecto:

    python -m scripts.create_super_admin

Te pide nombres, apellidos, correo y contraseña (mínimo 12 caracteres; se
escribe oculta y se confirma). Opcionalmente acepta argumentos
(--first-name, --last-name, --email) y la variable de entorno
SUPERADMIN_PASSWORD para automatizar.

Cómo funciona por dentro:
  1. Valida los datos.
  2. Llama a UserService.create_super_admin (services/user_service.py), que
     comprueba que no exista otro SUPER_ADMIN ni el mismo correo.
  3. La contraseña se guarda como hash Argon2id (core/security.py).
  4. Si dos procesos intentaran crear dos SUPER_ADMIN a la vez, MySQL lo
     impide con la restricción UNIQUE de `users.super_admin_slot`.
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

# Permite ejecutarlo también como `python scripts/create_super_admin.py`
# (agrega la raíz del proyecto al path de imports).
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pydantic import TypeAdapter, ValidationError  # noqa: E402
from pydantic import EmailStr  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from app.core.exceptions import AppError  # noqa: E402
from app.core.security import validate_password_strength  # noqa: E402
from app.infrastructure.database.session import SessionLocal  # noqa: E402
from app.services import UserService  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Lee los argumentos opcionales de la línea de comandos."""
    parser = argparse.ArgumentParser(description="Crear el SUPER_ADMIN de Harmony Spa")
    parser.add_argument("--first-name")
    parser.add_argument("--last-name")
    parser.add_argument("--email")
    parser.add_argument(
        "--password",
        help="No recomendado: queda en el historial de la consola. "
        "Mejor omítelo para que se pida de forma oculta.",
    )
    return parser.parse_args()


def ask(label: str, current: str | None) -> str:
    """Devuelve el valor recibido por argumento o lo pregunta en consola."""
    value = current or input(f"{label}: ").strip()
    if not value:
        raise SystemExit(f"[ERROR] {label} es obligatorio")
    return value


def ask_password(current: str | None) -> str:
    """Obtiene la contraseña: argumento, variable de entorno o consola oculta."""
    password = current or os.environ.get("SUPERADMIN_PASSWORD")
    if password:
        return password

    # getpass no muestra lo que se escribe.
    password = getpass.getpass("Crea una contraseña (mínimo 12 caracteres): ")
    confirm = getpass.getpass("Confirma la contraseña: ")
    if password != confirm:
        raise SystemExit("[ERROR] Las contraseñas no coinciden")
    return password


def main() -> int:
    """Flujo principal. Devuelve 0 si todo salió bien y 1 si hubo error."""
    args = parse_args()

    print("\n=== CREACIÓN DEL SUPER_ADMIN ===\n")

    first_name = ask("Nombres", args.first_name)
    last_name = ask("Apellidos", args.last_name)
    email = ask("Correo electrónico", args.email)
    password = ask_password(args.password)

    # 1. Validar formato del correo y la política de contraseñas (12+ caracteres).
    try:
        email = str(TypeAdapter(EmailStr).validate_python(email))
        validate_password_strength(password)
    except (ValidationError, ValueError) as exc:
        print(f"\n[ERROR] Datos inválidos: {exc}")
        return 1

    # 2. Crear el usuario mediante la capa de servicios.
    try:
        with SessionLocal() as db:
            user = UserService(db).create_super_admin(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
            )
    except AppError as exc:
        # Ejemplos: ya existe un SUPER_ADMIN, o el correo ya está registrado.
        print(f"\n[ERROR] {exc.detail}")
        return 1
    except SQLAlchemyError as exc:
        print(
            "\n[ERROR] No se pudo usar la base de datos. Verifica DATABASE_URL en .env "
            "y que hayas ejecutado: alembic upgrade head"
        )
        print(f"        Detalle: {exc.__class__.__name__}")
        return 1

    print("\nSUPER_ADMIN creado correctamente.")
    print(f"Identificador: {user.id}")
    print(f"Correo: {user.email}")
    print("La contraseña se almacenó mediante Argon2id.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

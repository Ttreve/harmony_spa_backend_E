"""Seguridad: contraseñas (Argon2id con pwdlib) y tokens de acceso (JWT con PyJWT).

Este módulo NO toca la base de datos: solo contiene funciones puras que usan
los servicios (`AuthService`, `UserService`) y los esquemas Pydantic.

Dos responsabilidades:
  1. Contraseñas -> `hash_password`, `verify_password`, `validate_password_strength`
     Nunca se guarda la contraseña original en MySQL: solo su hash Argon2id.
  2. Tokens JWT  -> `create_access_token`, `decode_access_token`
     Cada token lleva un `jti` (ID único) que enlaza con la tabla user_sessions.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# =====================================================================
# 1. CONTRASEÑAS
# =====================================================================

PASSWORD_MIN_LENGTH = 12
# Tope para evitar que alguien envíe contraseñas gigantes y sature el servidor
# (Argon2 es costoso a propósito). Coincide con max_length=128 de los esquemas.
PASSWORD_MAX_LENGTH = 128

# Argon2id: el algoritmo recomendado hoy para proteger contraseñas.
# `recommended()` aplica los parámetros seguros por defecto de pwdlib.
password_hasher = PasswordHash.recommended()


def validate_password_strength(password: str) -> str:
    """Valida la política de contraseñas. Lanza ValueError si no se cumple.

    Política: mínimo 12 caracteres, al menos una letra y un número.
    Se usa en los esquemas (UserCreate, ChangePasswordRequest), en
    `hash_password` y en el script que crea el SUPER_ADMIN.
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres."
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"La contraseña no puede superar {PASSWORD_MAX_LENGTH} caracteres."
        )
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValueError("La contraseña debe contener al menos una letra y un número.")
    return password


def hash_password(password: str) -> str:
    """Recibe una contraseña y devuelve su hash Argon2id.

    El resultado es lo que se guarda en `users.password_hash`
    (empieza por "$argon2id$..."). La contraseña original nunca se almacena.
    """
    validate_password_strength(password)
    return password_hasher.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Comprueba si una contraseña coincide con el hash almacenado.

    Devuelve False (nunca lanza error) si la contraseña no coincide, es
    demasiado larga o el hash guardado tiene un formato inválido.
    """
    if len(plain_password) > PASSWORD_MAX_LENGTH:
        return False
    try:
        return password_hasher.verify(plain_password, password_hash)
    except Exception:
        # Hash con formato desconocido o corrupto: se trata como "no coincide".
        return False


@lru_cache
def _dummy_hash() -> str:
    """Hash falso, calculado una sola vez, para `dummy_verify`."""
    return hash_password("Dummy-password-1")


def dummy_verify(plain_password: str) -> None:
    """Gasta el mismo tiempo que una verificación real.

    `AuthService.login` la llama cuando el correo NO existe, para que el tiempo
    de respuesta no revele qué correos están registrados (ataque de temporización).
    """
    verify_password(plain_password, _dummy_hash())


# =====================================================================
# 2. TOKENS JWT
# =====================================================================


@dataclass(frozen=True)
class TokenPayload:
    """Datos que `decode_access_token` extrae de un JWT válido."""

    user_id: int  # claim "sub"
    role: str  # claim "role"
    jti: str  # claim "jti": identifica la fila de user_sessions


def generate_jti() -> str:
    """Identificador único del token (UUID de 36 caracteres).

    Cabe exactamente en `user_sessions.jti` (String(36), único).
    """
    return str(uuid.uuid4())


def create_access_token(
    *,
    user_id: int,
    role: str,
    jti: str,
    expires_at: datetime,
) -> str:
    """Crea un JWT firmado con SECRET_KEY.

    `expires_at` es un datetime UTC *sin* zona horaria: el mismo valor que se
    guarda en `user_sessions.expires_at`, así token y sesión vencen a la vez.
    """
    payload = {
        "sub": str(user_id),  # a quién pertenece el token
        "role": role,
        "jti": jti,  # enlace con user_sessions
        "iat": datetime.now(timezone.utc),  # cuándo se emitió
        "exp": expires_at.replace(tzinfo=timezone.utc),  # cuándo vence
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> TokenPayload | None:
    """Verifica firma y vencimiento. Devuelve None si el token no es válido.

    Ojo: que el JWT sea válido NO basta para dejar pasar la petición;
    `AuthService.authenticate` además consulta la sesión en la base de datos.
    """
    try:
        data = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            # El token debe traer estos claims obligatoriamente.
            options={"require": ["exp", "sub", "jti"]},
        )
        return TokenPayload(
            user_id=int(data["sub"]),
            role=str(data.get("role", "")),
            jti=str(data["jti"]),
        )
    except (jwt.PyJWTError, KeyError, ValueError):
        return None

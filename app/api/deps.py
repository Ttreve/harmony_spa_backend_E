"""Dependencias compartidas de la API: usuario autenticado y control por roles.

Un endpoint se protege declarando una de estas dependencias:

    user: User = Depends(get_current_user)            # cualquier usuario con sesión
    actor: User = Depends(require_roles(UserRole.ADMIN, ...))   # solo ciertos roles

Cadena de dependencias:
    bearer_scheme  ->  get_auth_context  ->  get_current_user  ->  require_roles
    (lee el token)     (valida con AuthService)  (extrae el usuario)  (revisa el rol)
"""

from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.domain.enums.user_role import UserRole
from app.infrastructure.database.session import get_db
from app.models import User, UserSession
from app.services import AuthService

# Lee el encabezado "Authorization: Bearer <token>". Además hace aparecer el
# botón "Authorize" en Swagger (/docs). auto_error=False: el error 401 lo
# generamos nosotros para mantener el mismo formato de respuesta.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Pega el access_token que devuelve POST /auth/login",
)


@dataclass(frozen=True)
class AuthContext:
    """Usuario autenticado + la sesión (fila de user_sessions) de su token."""

    user: User
    session: UserSession


def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthContext:
    """Valida el token de la petición y devuelve usuario y sesión.

    Lanza 401 si falta el token o la sesión no es válida. Se usa directamente
    cuando el endpoint necesita la sesión (logout, cambio de contraseña).
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("No autenticado")
    user, session = AuthService(db).authenticate(credentials.credentials)
    return AuthContext(user=user, session=session)


def get_current_user(ctx: AuthContext = Depends(get_auth_context)) -> User:
    """Solo el usuario autenticado (para endpoints que no necesitan la sesión)."""
    return ctx.user


def require_roles(*roles: UserRole):
    """Dependencia que solo deja pasar a usuarios con alguno de los roles dados.

    Responde 401 si no hay sesión y 403 si el rol no está permitido.
    """
    allowed = frozenset(roles)

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise ForbiddenError("No tienes permisos para realizar esta acción")
        return user

    return dependency

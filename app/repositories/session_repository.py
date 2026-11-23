"""Repositorio de la tabla `user_sessions` (sesiones de login)."""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import UserSession


class SessionRepository:
    """Acceso a datos de user_sessions. No hace commit: lo decide el servicio."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, session: UserSession) -> UserSession:
        """Agrega una sesión nueva (flush deja disponible su id sin confirmar)."""
        self.db.add(session)
        self.db.flush()
        return session

    def get_by_jti(self, jti: str) -> UserSession | None:
        """Busca la sesión que corresponde al `jti` de un token."""
        stmt = select(UserSession).where(UserSession.jti == jti)
        return self.db.execute(stmt).scalar_one_or_none()

    def revoke(self, session: UserSession, now: datetime) -> None:
        """Marca UNA sesión como cerrada (logout, expiración o inactividad)."""
        session.is_active = False
        session.revoked_at = now

    def revoke_all_for_user(
        self,
        user_id: int,
        now: datetime,
        *,
        except_jti: str | None = None,
    ) -> None:
        """Cierra TODAS las sesiones activas de un usuario.

        `except_jti` permite conservar una (por ejemplo, la sesión actual al
        cambiar la contraseña). Se usa al desactivar un usuario o cambiar clave.
        """
        stmt = (
            update(UserSession)
            .where(UserSession.user_id == user_id)
            .where(UserSession.is_active.is_(True))
        )
        if except_jti is not None:
            stmt = stmt.where(UserSession.jti != except_jti)
        self.db.execute(stmt.values(is_active=False, revoked_at=now))

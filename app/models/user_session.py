"""Modelo UserSession -> tabla `user_sessions`.

Cada inicio de sesión (login) crea UNA fila aquí. Es lo que permite:
  - tener varias sesiones simultáneas por usuario (PC + celular),
  - cerrar una sesión concreta (logout) sin afectar las demás,
  - vencer la sesión por inactividad (30 min) o por tiempo máximo (2 h).

La lógica que revisa estos campos está en app/services/auth_service.py;
aquí solo se define la estructura de la tabla.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.models.user import utc_now_naive


class UserSession(Base):
    __tablename__ = "user_sessions"

    __table_args__ = (
        # Buscar rápido las sesiones activas de un usuario.
        Index(
            "ix_user_sessions_user_active",
            "user_id",
            "is_active"
        ),
        # Buscar rápido sesiones vencidas (limpieza futura).
        Index(
            "ix_user_sessions_expires_at",
            "expires_at"
        ),
    )

    # Identificador de la sesión
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Usuario propietario de la sesión
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Identificador único del JWT (claim "jti"). Une el token con esta fila:
    # al llegar un token, se busca la sesión por su jti.
    jti: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True
    )

    # Fecha de creación (inicio de sesión)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now_naive,
        server_default=func.current_timestamp()
    )

    # Última actividad del usuario: se actualiza en cada petición autenticada.
    # Controla los 30 minutos de inactividad.
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now_naive
    )

    # Vencimiento absoluto del token: máximo 2 horas desde el login,
    # sin importar la actividad.
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    # Cuándo se cerró o revocó la sesión (NULL = nunca se ha revocado).
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    # Estado de la sesión: False = cerrada/revocada, el token ya no sirve.
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    # Información del dispositivo desde el que se inició sesión.
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # 45 caracteres alcanzan para una IPv6
        nullable=True
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True
    )

    # Relación con el usuario propietario.
    user = relationship(
        "User",
        back_populates="sessions"
    )

"""Modelo User -> tabla `users`.

Representa a todas las personas que pueden entrar al sistema: SUPER_ADMIN,
ADMIN, ESTETICISTA y CLIENTE (el rol se guarda en la columna `role`).
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Integer,
    String,
    UniqueConstraint,
    Index,
    Boolean,
    DateTime,
    Enum as SAEnum,
    Computed,
    func,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums.user_role import UserRole
from app.infrastructure.database.base import Base


def utc_now_naive() -> datetime:
    """Fecha y hora UTC sin zona horaria.

    Se guarda así en MySQL DATETIME para que todas las fechas del proyecto
    (sesiones, vencimientos, inactividad) se comparen de forma consistente.
    Se reutiliza en user_session.py, auth_service.py y user_service.py.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        # Garantiza a nivel de BASE DE DATOS que solo exista un SUPER_ADMIN
        # (ver la columna `super_admin_slot` más abajo).
        UniqueConstraint(
            "super_admin_slot",
            name="uq_users_single_super_admin"
        ),
        # Acelera las consultas que filtran por rol y estado.
        Index(
            "ix_users_role_active",
            "role",
            "is_active"
        ),
    )

    # Identificador principal
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # --- Información personal ---
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    # Correo de acceso (se guarda en minúsculas y es único).
    email: Mapped[str] = mapped_column(
        String(254),
        nullable=False,
        unique=True
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    # --- Seguridad ---
    # Hash Argon2id de la contraseña (ver app/core/security.py).
    # Nunca se guarda la contraseña original.
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    # Rol del usuario. Se guarda como texto (VARCHAR) con una restricción
    # CHECK que solo admite los valores de UserRole.
    role: Mapped[UserRole] = mapped_column(
        SAEnum(
            UserRole,
            values_callable=lambda cls: [
                role.value for role in cls
            ],
            native_enum=False,
            create_constraint=True,
            length=20,
            name="user_role",
        ),
        nullable=False
    )

    # Estado de la cuenta: False = desactivada (borrado lógico, no se elimina la fila).
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    # --- Fechas de auditoría (las rellena MySQL) ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )

    # Restricción para permitir un solo SUPER_ADMIN.
    # Columna GENERADA por MySQL: vale 1 si role = 'SUPER_ADMIN' y NULL en los
    # demás casos. Como la columna es UNIQUE y MySQL permite varios NULL, solo
    # puede existir una fila con valor 1. No se escribe desde Python.
    super_admin_slot: Mapped[int | None] = mapped_column(
        Integer,
        Computed(
            "CASE WHEN role = 'SUPER_ADMIN' THEN 1 ELSE NULL END",
            persisted=True
        ),
        nullable=True
    )

    # Relación con las sesiones del usuario (un usuario puede tener varias
    # abiertas a la vez: computador y celular). Si se borra el usuario, MySQL
    # elimina sus sesiones (ON DELETE CASCADE).
    sessions = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    # Perfil de cliente (solo si role = CLIENTE). uselist=False = uno a uno.
    client_profile = relationship(
        "ClientProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    # Perfil de empleado (solo si role = ADMIN o ESTETICISTA).
    employee_profile = relationship(
        "EmployeeProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True
    )

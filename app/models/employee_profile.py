"""Modelo EmployeeProfile -> tabla `employee_profiles`.

Datos adicionales de los empleados del spa: usuarios con rol ADMIN o
ESTETICISTA. El rol real se sigue gestionando en `users.role`.

Pendiente (lógica de negocio): validar que solo una ESTETICISTA pueda ser
asignada a una cita.
"""

from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"

    __table_args__ = (
        # Buscar rápido empleados disponibles.
        Index("ix_employee_profiles_available", "is_available"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Usuario dueño del perfil (uno a uno).
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # Cargo (ej. "Esteticista", "Recepcionista").
    job_title: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    specialty: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    hire_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    # ¿Puede recibir citas? (independiente de users.is_active)
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # Relaciones
    user = relationship(
        "User",
        back_populates="employee_profile"
    )

    # Citas asignadas a este empleado (como esteticista).
    appointments = relationship(
        "Appointment",
        back_populates="esthetician",
        passive_deletes=True
    )

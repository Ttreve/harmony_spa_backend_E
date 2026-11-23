"""Modelo Procedure -> tabla `procedures`.

Catálogo de servicios que ofrece Harmony Spa: limpieza facial, masajes,
tratamientos corporales, etc.
"""

from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class Procedure(Base):
    __tablename__ = "procedures"

    __table_args__ = (
        # La base de datos rechaza duraciones y precios inválidos.
        CheckConstraint(
            "duration_minutes > 0",
            name="ck_procedures_duration_positive"
        ),
        CheckConstraint(
            "price >= 0",
            name="ck_procedures_price_nonnegative"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    # Dinero: Numeric(10, 2), nunca float (evita errores de precisión).
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    # Sesiones previstas del procedimiento, ordenadas por número de sesión.
    procedure_sessions = relationship(
        "ProcedureSession",
        back_populates="procedure",
        cascade="all, delete-orphan",
        order_by="ProcedureSession.session_number"
    )

    appointments = relationship(
        "Appointment",
        back_populates="procedure",
        passive_deletes=True
    )

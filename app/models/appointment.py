"""Modelo Appointment -> tabla `appointments` (reservas).

Permite: registrar qué cliente reservó, qué procedimiento pidió, asignar una
esteticista (opcional), fecha/hora de inicio y fin, controlar el estado y
registrar cancelaciones con su posible penalización.

La penalización se guarda como IMPORTE ya calculado (no como porcentaje). La
regla del 10% se aplicará después, en el servicio de cancelaciones.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums.appointment_status import AppointmentStatus
from app.infrastructure.database.base import Base


class Appointment(Base):
    __tablename__ = "appointments"

    __table_args__ = (
        CheckConstraint(
            "end_at > start_at",
            name="ck_appointments_valid_time"
        ),
        CheckConstraint(
            "cancellation_penalty >= 0",
            name="ck_appointments_penalty_nonnegative"
        ),
        # Índices para las consultas más comunes (agenda por cliente,
        # por esteticista y por estado).
        Index(
            "ix_appointments_client_start",
            "client_id",
            "start_at"
        ),
        Index(
            "ix_appointments_esthetician_start",
            "esthetician_id",
            "start_at"
        ),
        Index(
            "ix_appointments_status_start",
            "status",
            "start_at"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # RESTRICT: no se puede borrar un cliente o procedimiento con citas.
    client_id: Mapped[int] = mapped_column(
        ForeignKey("client_profiles.id", ondelete="RESTRICT"),
        nullable=False
    )

    procedure_id: Mapped[int] = mapped_column(
        ForeignKey("procedures.id", ondelete="RESTRICT"),
        nullable=False
    )

    # Esteticista asignada (puede quedar sin asignar). Si se elimina el
    # empleado, la cita se conserva con este campo en NULL.
    esthetician_id: Mapped[int | None] = mapped_column(
        ForeignKey("employee_profiles.id", ondelete="SET NULL"),
        nullable=True
    )

    start_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    end_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    status: Mapped[AppointmentStatus] = mapped_column(
        SAEnum(
            AppointmentStatus,
            values_callable=lambda enum_cls: [
                item.value for item in enum_cls
            ],
            native_enum=False,
            create_constraint=True,
            length=20,
            name="appointment_status"
        ),
        nullable=False,
        default=AppointmentStatus.PENDIENTE
    )

    cancellation_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    cancellation_penalty: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00")
    )

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

    # Relaciones
    client = relationship(
        "ClientProfile",
        back_populates="appointments"
    )

    procedure = relationship(
        "Procedure",
        back_populates="appointments"
    )

    esthetician = relationship(
        "EmployeeProfile",
        back_populates="appointments"
    )

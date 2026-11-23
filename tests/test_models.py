"""Pruebas del ORM: tablas registradas, relaciones y restricciones.

Se ejecutan sobre SQLite (nunca MySQL). Las llaves foráneas RESTRICT/SET NULL
solo las aplica MySQL, así que aquí se comprueban estructura y CHECKs.
"""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.domain.enums.appointment_status import AppointmentStatus
from app.domain.enums.user_role import UserRole
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import SessionLocal
from app.models import (
    Appointment,
    ClientProfile,
    EmployeeProfile,
    Procedure,
    ProcedureSession,
    User,
)
from tests.conftest import PASSWORD


def _user(email: str, role: UserRole) -> User:
    return User(
        first_name="Nombre",
        last_name="Apellido",
        email=email,
        password_hash=hash_password(PASSWORD),
        role=role,
    )


def test_all_tables_are_registered():
    assert set(Base.metadata.tables) == {
        "users",
        "user_sessions",
        "client_profiles",
        "employee_profiles",
        "procedures",
        "procedure_sessions",
        "appointments",
    }


def _create_appointment(db) -> Appointment:
    client_user = _user("cliente@harmonyspa.co", UserRole.CLIENTE)
    client_user.client_profile = ClientProfile(address="Bogota")
    staff_user = _user("laura@harmonyspa.co", UserRole.ESTETICISTA)
    staff_user.employee_profile = EmployeeProfile(job_title="Esteticista")
    procedure = Procedure(
        name="Limpieza facial",
        duration_minutes=60,
        price=Decimal("85000.50"),
        procedure_sessions=[
            ProcedureSession(session_number=2, title="Segunda", duration_minutes=30),
            ProcedureSession(session_number=1, title="Primera", duration_minutes=45),
        ],
    )
    db.add_all([client_user, staff_user, procedure])
    db.flush()

    appointment = Appointment(
        client_id=client_user.client_profile.id,
        procedure_id=procedure.id,
        esthetician_id=staff_user.employee_profile.id,
        start_at=datetime(2026, 12, 1, 9, 0),
        end_at=datetime(2026, 12, 1, 10, 0),
    )
    db.add(appointment)
    db.commit()
    return appointment


def test_relationships_and_defaults():
    with SessionLocal() as db:
        appointment = _create_appointment(db)
        db.refresh(appointment)

        # Valores por defecto
        assert appointment.status == AppointmentStatus.PENDIENTE
        assert appointment.cancellation_penalty == Decimal("0.00")
        # Relaciones de ida y vuelta
        assert appointment.client.user.email == "cliente@harmonyspa.co"
        assert appointment.esthetician.user.role == UserRole.ESTETICISTA
        assert appointment.procedure.price == Decimal("85000.50")
        assert appointment.client.appointments == [appointment]
        # Las sesiones del procedimiento salen ordenadas por session_number
        numbers = [s.session_number for s in appointment.procedure.procedure_sessions]
        assert numbers == [1, 2]


def test_appointment_end_must_be_after_start():
    with SessionLocal() as db:
        appointment = _create_appointment(db)
        db.add(
            Appointment(
                client_id=appointment.client_id,
                procedure_id=appointment.procedure_id,
                start_at=datetime(2026, 12, 1, 10, 0),
                end_at=datetime(2026, 12, 1, 9, 0),  # termina antes de empezar
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_procedure_rejects_negative_price():
    with SessionLocal() as db:
        db.add(Procedure(name="Masaje", duration_minutes=30, price=Decimal("-1")))
        with pytest.raises(IntegrityError):
            db.commit()


def test_procedure_session_number_is_unique_per_procedure():
    with SessionLocal() as db:
        procedure = Procedure(name="Drenaje", duration_minutes=40, price=Decimal("50000"))
        db.add(procedure)
        db.flush()
        db.add_all(
            [
                ProcedureSession(
                    procedure_id=procedure.id, session_number=1, title="A", duration_minutes=20
                ),
                ProcedureSession(
                    procedure_id=procedure.id, session_number=1, title="B", duration_minutes=20
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            db.commit()

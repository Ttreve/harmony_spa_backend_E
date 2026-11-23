"""Modelos ORM (una clase = una tabla de MySQL).

Importarlos aquí permite `from app.models import User, UserSession, ...` y,
sobre todo, que Alembic los registre en `Base.metadata` (migrations/env.py).
Al crear un modelo nuevo, agrégalo a este archivo.

Mapa de tablas:
    users ──< user_sessions            (sesiones de login)
    users ──1 client_profiles          (solo rol CLIENTE)
    users ──1 employee_profiles        (solo rol ADMIN / ESTETICISTA)
    procedures ──< procedure_sessions  (cómo se compone un procedimiento)
    appointments  -> client_profiles + procedures + employee_profiles (esteticista)
"""

from app.models.user import User
from app.models.user_session import UserSession
from app.models.client_profile import ClientProfile
from app.models.employee_profile import EmployeeProfile
from app.models.procedure import Procedure
from app.models.procedure_session import ProcedureSession
from app.models.appointment import Appointment

__all__ = [
    "User",
    "UserSession",
    "ClientProfile",
    "EmployeeProfile",
    "Procedure",
    "ProcedureSession",
    "Appointment",
]

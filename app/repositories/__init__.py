"""Repositorios: acceso a datos (consultas SQL con SQLAlchemy).

Aquí NO hay reglas de negocio ni commit: solo leer/escribir tablas.
Los servicios (app/services) deciden cuándo confirmar con `db.commit()`.
"""

from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository

__all__ = ["SessionRepository", "UserRepository"]

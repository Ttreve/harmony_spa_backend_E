"""Esquemas Pydantic: forma de los datos que entran y salen de la API.

Validan el JSON recibido (ej. LoginRequest) y definen lo que se devuelve
(ej. UserResponse, que nunca incluye password_hash).
"""

from app.schemas.auth import LoginRequest, MessageResponse, TokenResponse
from app.schemas.user import (
    ChangePasswordRequest,
    ClientProfileCreate,
    EmployeeProfileCreate,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserSelfUpdate,
    UserStatusUpdate,
    UserUpdate,
)

__all__ = [
    "ChangePasswordRequest",
    "ClientProfileCreate",
    "EmployeeProfileCreate",
    "LoginRequest",
    "MessageResponse",
    "TokenResponse",
    "UserCreate",
    "UserListResponse",
    "UserResponse",
    "UserSelfUpdate",
    "UserStatusUpdate",
    "UserUpdate",
]

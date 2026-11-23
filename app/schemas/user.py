"""Esquemas de usuarios: crear (con su perfil), editar, cambiar estado y leer.

Pydantic valida los datos que llegan a la API y define lo que devuelve.
La política de contraseñas NO se repite aquí: se reutiliza
`validate_password_strength` de app/core/security.py. `password_hash` jamás
aparece en una respuesta.
"""

import re
from datetime import date, datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.core.security import validate_password_strength
from app.domain.enums.user_role import UserRole

_PHONE_PATTERN = re.compile(r"^\+?[0-9\s\-()]{7,30}$")


# ---------------------------------------------------------------------------
# Funciones de limpieza reutilizadas por varios esquemas
# ---------------------------------------------------------------------------
def _clean_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("No puede estar vacío")
    return value


def _clean_phone(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not _PHONE_PATTERN.match(value):
        raise ValueError("Teléfono inválido")
    return value


# ---------------------------------------------------------------------------
# Perfiles que se envían al crear un usuario
# ---------------------------------------------------------------------------
class ClientProfileCreate(BaseModel):
    """Datos adicionales de un CLIENTE (tabla client_profiles)."""

    birth_date: date | None = None
    address: str | None = Field(default=None, max_length=255)
    emergency_contact_name: str | None = Field(default=None, max_length=150)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)
    notes: str | None = None


class EmployeeProfileCreate(BaseModel):
    """Datos adicionales de un empleado: ADMIN o ESTETICISTA (employee_profiles)."""

    job_title: str = Field(min_length=2, max_length=100)
    specialty: str | None = Field(default=None, max_length=150)
    hire_date: date | None = None
    is_available: bool = True
    notes: str | None = None


# ---------------------------------------------------------------------------
# Crear usuario
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    """Cuerpo de POST /users. Incluye el perfil que corresponde al rol."""

    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=12, max_length=128)
    role: UserRole

    client_profile: ClientProfileCreate | None = None
    employee_profile: EmployeeProfileCreate | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_names(cls, value: str) -> str:
        return _clean_name(value)

    @field_validator("email")
    @classmethod
    def lower_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, value: str | None) -> str | None:
        return _clean_phone(value)

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        # 12+ caracteres con al menos una letra y un número.
        return validate_password_strength(value)

    @model_validator(mode="after")
    def validate_role_profiles(self):
        """Cada rol exige SU perfil y rechaza el del otro tipo."""
        if self.role == UserRole.SUPER_ADMIN:
            raise ValueError("El SUPER_ADMIN no se puede crear desde este endpoint.")

        if self.role == UserRole.CLIENTE:
            if self.client_profile is None:
                raise ValueError("El cliente debe tener un perfil de cliente.")
            if self.employee_profile is not None:
                raise ValueError("Un cliente no puede tener perfil de empleado.")

        elif self.role in (UserRole.ADMIN, UserRole.ESTETICISTA):
            if self.employee_profile is None:
                raise ValueError("El empleado debe tener un perfil de empleado.")
            if self.client_profile is not None:
                raise ValueError("Un empleado no puede tener perfil de cliente.")

        return self


# ---------------------------------------------------------------------------
# Actualizar usuario
# ---------------------------------------------------------------------------
class _NoNullFieldsMixin(BaseModel):
    """Impide enviar null explícito en campos obligatorios en la base de datos."""

    @field_validator(
        "first_name", "last_name", "email", mode="before", check_fields=False
    )
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("No puede ser null")
        return value


class UserUpdate(_NoNullFieldsMixin):
    """Cuerpo de PATCH /users/{id}. Todos los campos son opcionales.

    NO permite cambiar el rol (no se promueve/degrada con una edición
    ordinaria) ni el estado (para eso existe PATCH /users/{id}/status).
    """

    first_name: str | None = Field(default=None, min_length=2, max_length=100)
    last_name: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_names(cls, value: str | None) -> str | None:
        return None if value is None else _clean_name(value)

    @field_validator("email")
    @classmethod
    def lower_email(cls, value: str | None) -> str | None:
        return None if value is None else value.strip().lower()

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, value: str | None) -> str | None:
        return _clean_phone(value)


class UserStatusUpdate(BaseModel):
    """Cuerpo de PATCH /users/{id}/status: activar o desactivar la cuenta."""

    is_active: bool


# ---------------------------------------------------------------------------
# Perfil propio (/users/me)
# ---------------------------------------------------------------------------
class UserSelfUpdate(_NoNullFieldsMixin):
    """Edición del propio perfil (no permite cambiar correo, rol ni estado)."""

    first_name: str | None = Field(default=None, min_length=2, max_length=100)
    last_name: str | None = Field(default=None, min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_names(cls, value: str | None) -> str | None:
        return None if value is None else _clean_name(value)

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, value: str | None) -> str | None:
        return _clean_phone(value)


class ChangePasswordRequest(BaseModel):
    """Cuerpo de POST /users/me/password."""

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return validate_password_strength(value)


# ---------------------------------------------------------------------------
# Respuestas
# ---------------------------------------------------------------------------
class UserResponse(BaseModel):
    """Usuario tal como lo devuelve la API (sin password_hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    """Respuesta paginada de GET /users."""

    items: list[UserResponse]
    total: int
    skip: int
    limit: int

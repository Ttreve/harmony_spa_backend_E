"""Esquemas de autenticación: login y respuesta con el token."""

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    """Cuerpo de POST /auth/login."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def lower_email(cls, value: str) -> str:
        return value.strip().lower()


class TokenResponse(BaseModel):
    """Respuesta del login: el token y los tiempos de la sesión."""

    access_token: str
    token_type: str = "bearer"
    # Segundos de vida máxima del token.
    expires_in: int
    # Segundos de inactividad tras los cuales la sesión se cierra.
    inactivity_timeout: int
    user: UserResponse


class MessageResponse(BaseModel):
    """Respuesta genérica con un mensaje (por ejemplo, logout)."""

    message: str

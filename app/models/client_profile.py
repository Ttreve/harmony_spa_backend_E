"""Modelo ClientProfile -> tabla `client_profiles`.

Datos adicionales que SOLO tienen los usuarios con rol CLIENTE.

¿Por qué separarlo de `users`? `users` guarda lo necesario para iniciar sesión
y manejar roles; este perfil guarda información propia del cliente.
Relación uno a uno: un usuario tiene como máximo un perfil de cliente.
"""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class ClientProfile(Base):
    __tablename__ = "client_profiles"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Usuario dueño del perfil. UNIQUE = un solo perfil por usuario.
    # Si se elimina el usuario, MySQL elimina también su perfil.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    birth_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    emergency_contact_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    emergency_contact_phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # Relaciones
    user = relationship(
        "User",
        back_populates="client_profile"
    )

    # Citas reservadas por este cliente.
    appointments = relationship(
        "Appointment",
        back_populates="client",
        passive_deletes=True
    )

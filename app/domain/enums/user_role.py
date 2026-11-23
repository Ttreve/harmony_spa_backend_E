"""Roles del sistema Harmony Spa.

Los roles viven en un Enum para tener valores controlados: así nadie guarda
"Administrador", "admin" y "ADMINISTRADOR" indistintamente.

Se usa en: models/user.py (columna `role`), core/permissions.py (jerarquía),
schemas/user.py (validación) y api/deps.py (`require_roles`).
"""

from enum import Enum


class UserRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"  # único; se crea solo con scripts/create_super_admin.py
    ADMIN = "ADMIN"
    ESTETICISTA = "ESTETICISTA"
    CLIENTE = "CLIENTE"

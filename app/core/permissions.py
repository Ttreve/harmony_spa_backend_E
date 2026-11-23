"""Reglas de permisos por rol (quién puede gestionar a quién).

Jerarquía:
    SUPER_ADMIN  >  ADMIN  >  ESTETICISTA = CLIENTE

- Un usuario solo puede gestionar (editar/desactivar) a usuarios de un rango
  estrictamente menor al suyo. Por eso nadie gestiona a un SUPER_ADMIN por la
  API, y cada usuario edita su propio perfil mediante /users/me.
- El SUPER_ADMIN nunca se crea por la API: solo con
  `python -m scripts.create_super_admin` (además, la base de datos solo admite
  uno: restricción UNIQUE sobre `users.super_admin_slot`).

NOTA: por ahora la gestión de usuarios (/users) está reservada al SUPER_ADMIN
(ver api/v1/users.py), así que estas reglas no se consultan en esas rutas.
Se conservan para cuando se definan permisos delegados al ADMIN ("según
autorización"). No dependen de la base de datos.
"""

from app.domain.enums.user_role import UserRole

# Rango numérico de cada rol: mayor número = más poder.
ROLE_RANK: dict[UserRole, int] = {
    UserRole.SUPER_ADMIN: 3,
    UserRole.ADMIN: 2,
    UserRole.ESTETICISTA: 1,
    UserRole.CLIENTE: 1,
}

# Qué roles puede ASIGNAR (al crear o editar) cada rol.
# SUPER_ADMIN no aparece como asignable: no se puede crear otro por la API.
ASSIGNABLE_ROLES: dict[UserRole, frozenset[UserRole]] = {
    UserRole.SUPER_ADMIN: frozenset(
        {UserRole.ADMIN, UserRole.ESTETICISTA, UserRole.CLIENTE}
    ),
    UserRole.ADMIN: frozenset({UserRole.ESTETICISTA, UserRole.CLIENTE}),
}


def assignable_roles(actor_role: UserRole) -> frozenset[UserRole]:
    """Roles que `actor_role` puede asignar. ESTETICISTA/CLIENTE: ninguno."""
    return ASSIGNABLE_ROLES.get(actor_role, frozenset())


def can_manage(actor_role: UserRole, target_role: UserRole) -> bool:
    """True si el actor tiene rango estrictamente mayor que el objetivo."""
    return ROLE_RANK[actor_role] > ROLE_RANK[target_role]

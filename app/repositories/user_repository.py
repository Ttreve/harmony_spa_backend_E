"""Repositorio de `users` y de sus perfiles (client_profiles / employee_profiles).

Solo consulta y guarda datos; las reglas de negocio están en UserService.
"""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domain.enums.user_role import UserRole
from app.models import ClientProfile, EmployeeProfile, User


class UserRepository:
    """Acceso a datos de la tabla users. No hace commit: lo decide el servicio."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        """Usuario por id, o None si no existe."""
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        """Usuario por correo (el correo ya debe venir en minúsculas)."""
        stmt = select(User).where(User.email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_super_admin(self) -> User | None:
        """El SUPER_ADMIN, o None si todavía no se ha creado."""
        stmt = select(User).where(User.role == UserRole.SUPER_ADMIN).limit(1)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_filtered(
        self,
        *,
        role: UserRole | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        """Lista usuarios con filtros y paginación.

        Devuelve (usuarios de la página, total que cumple los filtros).
        """
        stmt = select(User)

        if role is not None:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active.is_(is_active))
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )

        total = self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()

        items = (
            self.db.execute(stmt.order_by(User.id).offset(skip).limit(limit))
            .scalars()
            .all()
        )
        return list(items), total

    def add(self, user: User) -> User:
        """Agrega un usuario (flush deja disponible su id sin confirmar)."""
        self.db.add(user)
        self.db.flush()
        return user

    def add_client_profile(self, profile: ClientProfile) -> ClientProfile:
        """Agrega el perfil de un CLIENTE (el usuario ya debe tener id)."""
        self.db.add(profile)
        self.db.flush()
        return profile

    def add_employee_profile(self, profile: EmployeeProfile) -> EmployeeProfile:
        """Agrega el perfil de un empleado ADMIN/ESTETICISTA (el usuario ya debe tener id)."""
        self.db.add(profile)
        self.db.flush()
        return profile

"""Servicio de usuarios: crear (con perfil), listar, editar, activar/desactivar
y cambiar la contraseña propia.

Aquí viven las reglas de negocio:
  - sin correos duplicados,
  - la contraseña se guarda como hash Argon2id,
  - cada rol recibe su perfil (CLIENTE -> client_profiles,
    ADMIN/ESTETICISTA -> employee_profiles),
  - el SUPER_ADMIN no se crea, edita ni desactiva por la API,
  - el rol no se cambia con una edición ordinaria,
  - al desactivar una cuenta se revocan sus sesiones abiertas.

Los datos se leen/escriben mediante UserRepository y SessionRepository.
Los errores se lanzan como AppError (core/exceptions.py) y salen como JSON.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
)
from app.core.security import hash_password, verify_password
from app.domain.enums.user_role import UserRole
from app.models import ClientProfile, EmployeeProfile, User
from app.models.user import utc_now_naive
from app.repositories import SessionRepository, UserRepository
from app.schemas import UserCreate, UserSelfUpdate, UserUpdate


class UserService:
    """Reglas de negocio para la gestión de usuarios."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.sessions = SessionRepository(db)

    # ------------------------------------------------------------------
    # SUPER_ADMIN (solo desde scripts/create_super_admin.py)
    # ------------------------------------------------------------------
    def create_super_admin(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        password: str,
    ) -> User:
        """Crea el único SUPER_ADMIN. NO hay endpoint que llame a este método.

        Lo usa solo el script `python -m scripts.create_super_admin`.
        Doble protección contra duplicados: esta comprobación y, por debajo,
        la restricción UNIQUE de MySQL (`users.super_admin_slot`).
        """
        if self.users.get_super_admin() is not None:
            raise ConflictError("Ya existe un SUPER_ADMIN en el sistema")

        return self._create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=None,
            password=password,
            role=UserRole.SUPER_ADMIN,
        )

    # ------------------------------------------------------------------
    # Gestión de usuarios (API; solo SUPER_ADMIN)
    # ------------------------------------------------------------------
    def create_user(self, data: UserCreate) -> User:
        """Crea un usuario y el perfil que corresponde a su rol.

        UserCreate ya garantizó que el rol no sea SUPER_ADMIN y que traiga
        el perfil correcto (cliente o empleado).
        """
        return self._create(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            phone=data.phone,
            password=data.password,
            role=data.role,
            client_profile=(
                ClientProfile(**data.client_profile.model_dump())
                if data.client_profile
                else None
            ),
            employee_profile=(
                EmployeeProfile(**data.employee_profile.model_dump())
                if data.employee_profile
                else None
            ),
        )

    def list_users(
        self,
        *,
        role: UserRole | None,
        is_active: bool | None,
        search: str | None,
        skip: int,
        limit: int,
    ) -> tuple[list[User], int]:
        """Lista usuarios filtrados; devuelve (página, total)."""
        return self.users.list_filtered(
            role=role,
            is_active=is_active,
            search=search,
            skip=skip,
            limit=limit,
        )

    def get_user(self, user_id: int) -> User:
        """Obtiene un usuario o lanza 404 si no existe."""
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("No se encontró el usuario solicitado.")
        return user

    def update_user(self, user_id: int, data: UserUpdate) -> User:
        """Actualiza nombre, apellido, correo o teléfono (PATCH /users/{id}).

        No cambia rol ni estado. El SUPER_ADMIN no se modifica desde aquí.
        """
        user = self.get_user(user_id)

        if user.role == UserRole.SUPER_ADMIN:
            raise BadRequestError("No se puede modificar el SUPER_ADMIN desde este módulo.")

        # exclude_unset: solo los campos que el cliente realmente envió.
        changes = data.model_dump(exclude_unset=True)

        # Si cambia el correo, no puede pertenecer a otro usuario.
        if "email" in changes:
            existing = self.users.get_by_email(changes["email"])
            if existing is not None and existing.id != user.id:
                raise ConflictError("Ese correo electrónico ya está registrado.")

        for field, value in changes.items():
            setattr(user, field, value)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(
                "No fue posible actualizar el usuario. "
                "Verifica que el correo no esté duplicado."
            ) from exc

        self.db.refresh(user)
        return user

    def change_status(self, user_id: int, *, is_active: bool, current_user_id: int) -> User:
        """Activa o desactiva una cuenta (PATCH /users/{id}/status).

        Reglas: no se toca al SUPER_ADMIN y nadie se desactiva a sí mismo.
        Al DESACTIVAR se cierran todas sus sesiones abiertas; si luego se
        reactiva, la persona debe iniciar sesión de nuevo.
        """
        user = self.get_user(user_id)

        if user.role == UserRole.SUPER_ADMIN:
            raise BadRequestError("No se puede cambiar el estado del SUPER_ADMIN.")

        if user.id == current_user_id and not is_active:
            raise BadRequestError("No puedes desactivar tu propia cuenta.")

        user.is_active = is_active

        if not is_active:
            self.sessions.revoke_all_for_user(user.id, utc_now_naive())

        self.db.commit()
        self.db.refresh(user)
        return user

    # ------------------------------------------------------------------
    # Perfil propio (/users/me)
    # ------------------------------------------------------------------
    def update_me(self, user: User, data: UserSelfUpdate) -> User:
        """Edita el propio perfil (nombre, apellido, teléfono). No permite rol/estado."""
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    def change_password(
        self,
        user: User,
        *,
        current_password: str,
        new_password: str,
        current_jti: str,
    ) -> None:
        """Cambia la contraseña propia y cierra las demás sesiones.

        `current_jti` identifica la sesión actual, que se conserva abierta.
        """
        if not verify_password(current_password, user.password_hash):
            raise BadRequestError("La contraseña actual es incorrecta")

        if current_password == new_password:
            raise BadRequestError("La nueva contraseña debe ser distinta a la actual")

        user.password_hash = hash_password(new_password)
        # Se cierran las demás sesiones; la actual sigue activa.
        self.sessions.revoke_all_for_user(
            user.id, utc_now_naive(), except_jti=current_jti
        )
        self.db.commit()

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------
    def _create(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        phone: str | None,
        password: str,
        role: UserRole,
        client_profile: ClientProfile | None = None,
        employee_profile: EmployeeProfile | None = None,
    ) -> User:
        """Creación común a create_user y create_super_admin.

        Usuario y perfil se guardan en UNA sola transacción: si algo falla,
        no queda un usuario "a medias" sin su perfil.
        """
        email = email.strip().lower()

        if self.users.get_by_email(email) is not None:
            raise ConflictError("Ya existe un usuario registrado con ese correo.")

        user = User(
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=email,
            phone=phone,
            # Se guarda el hash Argon2id, nunca la contraseña original.
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )

        try:
            self.users.add(user)  # flush: ya tiene id

            # El perfil se enlaza con el id del usuario recién creado.
            if client_profile is not None and role == UserRole.CLIENTE:
                client_profile.user_id = user.id
                self.users.add_client_profile(client_profile)
            elif employee_profile is not None and role in (
                UserRole.ADMIN,
                UserRole.ESTETICISTA,
            ):
                employee_profile.user_id = user.id
                self.users.add_employee_profile(employee_profile)

            self.db.commit()
        except IntegrityError as exc:
            # MySQL rechazó el registro (correo repetido o segundo SUPER_ADMIN),
            # por ejemplo si dos peticiones llegaron al mismo tiempo.
            self.db.rollback()
            raise ConflictError(
                "No se pudo crear el usuario: el correo ya existe o ya hay un SUPER_ADMIN"
            ) from exc
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(user)
        return user

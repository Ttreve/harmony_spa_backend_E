"""Endpoints de usuarios: /api/v1/users/...

Dos grupos:
  - /users/me...      cualquier usuario autenticado (su propio perfil).
  - /users, /users/{id}...   gestión de usuarios: SOLO el SUPER_ADMIN.

| Método | Ruta                  | Quién          | Función                 |
|--------|-----------------------|----------------|-------------------------|
| GET    | /users/me             | autenticado    | Ver mi perfil           |
| PATCH  | /users/me             | autenticado    | Editar mi perfil        |
| POST   | /users/me/password    | autenticado    | Cambiar mi contraseña   |
| POST   | /users                | SUPER_ADMIN    | Crear usuario + perfil  |
| GET    | /users                | SUPER_ADMIN    | Listar (filtros)        |
| GET    | /users/{id}           | SUPER_ADMIN    | Consultar usuario       |
| PATCH  | /users/{id}           | SUPER_ADMIN    | Actualizar datos        |
| PATCH  | /users/{id}/status    | SUPER_ADMIN    | Activar / desactivar    |

No hay DELETE: los usuarios nunca se eliminan físicamente, solo se desactivan.
Las rutas /me se declaran ANTES que /{user_id} para que "me" no se interprete
como un id. Las reglas de negocio están en services/user_service.py.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_auth_context, get_current_user, require_roles
from app.domain.enums.user_role import UserRole
from app.infrastructure.database.session import get_db
from app.models import User
from app.schemas import (
    ChangePasswordRequest,
    MessageResponse,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserSelfUpdate,
    UserStatusUpdate,
    UserUpdate,
)
from app.services import UserService

router = APIRouter(prefix="/users", tags=["Gestión de usuarios"])

# Dependencia: solo deja pasar al SUPER_ADMIN (401 sin sesión, 403 otro rol).
require_super_admin = require_roles(UserRole.SUPER_ADMIN)


# ---------------------------------------------------------------------------
# Perfil propio (cualquier usuario autenticado)
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserResponse, summary="Ver mi perfil")
def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse, summary="Editar mi perfil")
def update_me(
    payload: UserSelfUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    return UserResponse.model_validate(UserService(db).update_me(user, payload))


@router.post(
    "/me/password",
    response_model=MessageResponse,
    summary="Cambiar mi contraseña",
)
def change_my_password(
    payload: ChangePasswordRequest,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> MessageResponse:
    UserService(db).change_password(
        ctx.user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        current_jti=ctx.session.jti,  # esta sesión se conserva abierta
    )
    return MessageResponse(
        message="Contraseña actualizada. Las demás sesiones fueron cerradas."
    )


# ---------------------------------------------------------------------------
# Gestión de usuarios (solo SUPER_ADMIN)
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario (con su perfil de cliente o de empleado)",
)
def create_user(
    payload: UserCreate,
    _actor: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> UserResponse:
    return UserResponse.model_validate(UserService(db).create_user(payload))


@router.get("", response_model=UserListResponse, summary="Listar usuarios")
def list_users(
    role: UserRole | None = None,
    is_active: bool | None = None,
    search: str | None = Query(default=None, max_length=100),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    _actor: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> UserListResponse:
    items, total = UserService(db).list_users(
        role=role,
        is_active=is_active,
        search=search,
        skip=skip,
        limit=limit,
    )
    return UserListResponse(
        items=[UserResponse.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{user_id}", response_model=UserResponse, summary="Consultar un usuario")
def get_user(
    user_id: int,
    _actor: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> UserResponse:
    return UserResponse.model_validate(UserService(db).get_user(user_id))


@router.patch("/{user_id}", response_model=UserResponse, summary="Actualizar datos de un usuario")
def update_user(
    user_id: int,
    payload: UserUpdate,
    _actor: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> UserResponse:
    return UserResponse.model_validate(UserService(db).update_user(user_id, payload))


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    summary="Activar o desactivar un usuario",
)
def change_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    actor: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> UserResponse:
    return UserResponse.model_validate(
        UserService(db).change_status(
            user_id,
            is_active=payload.is_active,
            current_user_id=actor.id,
        )
    )

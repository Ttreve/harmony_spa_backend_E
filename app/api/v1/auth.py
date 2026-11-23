"""Endpoints de autenticación: /api/v1/auth/...

  POST /auth/login   -> público; devuelve el access_token
  POST /auth/logout  -> cierra la sesión del token enviado (204 No Content)
  GET  /auth/me      -> datos del usuario de la sesión actual

Solo traducen HTTP <-> AuthService; las reglas están en services/auth_service.py.
"""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_auth_context
from app.core.config import settings
from app.infrastructure.database.session import get_db
from app.schemas import LoginRequest, TokenResponse, UserResponse
from app.services import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse, summary="Iniciar sesión")
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Valida credenciales, abre una sesión y entrega el token."""
    token, _expires_at, user = AuthService(db).login(
        payload.email,
        payload.password,
        # IP y navegador quedan registrados en user_sessions.
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    # Los tiempos se devuelven en segundos para que el frontend pueda
    # avisar al usuario antes de que la sesión termine.
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        inactivity_timeout=settings.INACTIVITY_TIMEOUT_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cerrar sesión",
)
def logout(
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> Response:
    """Revoca la sesión del token enviado (las demás siguen activas).

    Responde 204 No Content: la sesión se cerró y no hay cuerpo que devolver.
    """
    AuthService(db).logout(ctx.session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse, summary="Usuario de la sesión actual")
def me(ctx: AuthContext = Depends(get_auth_context)) -> UserResponse:
    """Devuelve el usuario dueño del token (útil para el frontend al cargar)."""
    return UserResponse.model_validate(ctx.user)

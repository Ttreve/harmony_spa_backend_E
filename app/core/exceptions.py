"""Errores de negocio de la aplicación.

Los servicios lanzan estas excepciones (`raise NotFoundError("...")`) sin
preocuparse por HTTP; `register_exception_handlers` las convierte en una
respuesta JSON con el código correcto: {"detail": "mensaje"}.

Jerarquía: AppError -> BadRequest (400), Unauthorized (401), Forbidden (403),
NotFound (404), Conflict (409).
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Error de negocio base que se traduce a una respuesta HTTP."""

    status_code: int = 400
    default_detail: str = "Error en la solicitud"
    headers: dict[str, str] | None = None

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class BadRequestError(AppError):
    """400: datos inválidos (por ejemplo, contraseña actual incorrecta)."""

    status_code = 400
    default_detail = "Solicitud inválida"


class UnauthorizedError(AppError):
    """401: no hay sesión válida (sin token, token vencido, sesión cerrada)."""

    status_code = 401
    default_detail = "No autenticado"
    # Encabezado estándar que indica al cliente que debe enviar un Bearer token.
    headers = {"WWW-Authenticate": "Bearer"}


class ForbiddenError(AppError):
    """403: está autenticado pero su rol no permite la acción."""

    status_code = 403
    default_detail = "No tienes permisos para realizar esta acción"


class NotFoundError(AppError):
    """404: el recurso pedido no existe."""

    status_code = 404
    default_detail = "Recurso no encontrado"


class ConflictError(AppError):
    """409: choca con algo existente (correo repetido, segundo SUPER_ADMIN)."""

    status_code = 409
    default_detail = "El recurso ya existe"


def register_exception_handlers(application: FastAPI) -> None:
    """Conecta AppError con FastAPI. Se llama una vez desde app/main.py."""

    @application.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        # Mismo formato que HTTPException: {"detail": "..."}
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

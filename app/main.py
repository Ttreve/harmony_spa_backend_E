"""Punto de entrada de la aplicación.

Arrancar:  uvicorn app.main:app --reload
Aquí se arma la app: CORS, manejo de errores y routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.api.health import health_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers


def create_application() -> FastAPI:
    """Fábrica de la aplicación (también la usan las pruebas)."""
    application = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        debug=settings.DEBUG,
        description="API REST del sistema Harmony Spa.",
    )

    # El frontend envía el token en el encabezado Authorization (no en cookies),
    # por eso no se habilitan credenciales.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Convierte los errores de negocio (AppError) en respuestas JSON.
    register_exception_handlers(application)

    # /health y /health/ready (sin prefijo).
    application.include_router(health_router)

    # /api/v1/auth/..., /api/v1/users/... (ver app/api/v1/router.py).
    application.include_router(
        api_router,
        prefix=settings.API_V1_PREFIX,
    )

    return application


app = create_application()

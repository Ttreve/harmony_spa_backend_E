"""Router principal de la versión 1 de la API (prefijo /api/v1).

Aquí se registra cada módulo de endpoints. Al crear uno nuevo
(clientes, citas, tratamientos...), inclúyelo con `include_router`.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router

api_router = APIRouter()

api_router.include_router(auth_router)  # /auth/...
api_router.include_router(users_router)  # /users/...

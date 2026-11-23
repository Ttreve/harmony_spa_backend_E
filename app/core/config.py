"""Configuración central del proyecto.

Lee las variables del archivo `.env` (raíz del proyecto) y las expone como
`settings`. Cualquier archivo que necesite un valor de configuración debe
importarlo desde aquí:

    from app.core.config import settings

Para agregar una variable nueva: declárala en `Settings` y en `.env.example`.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Aplicación ---
    APP_NAME: str = "Harmony Spa API"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # --- Base de datos ---
    # Obligatoria: no tiene valor por defecto, debe venir del .env.
    DATABASE_URL: str

    # --- Autenticación ---
    # Clave secreta con la que se firman los JWT. Obligatoria.
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    # Vida máxima absoluta de la sesión/token: 2 horas (120 minutos).
    # Se guarda en user_sessions.expires_at.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=120, gt=0)
    # Minutos sin actividad tras los cuales la sesión se cierra (30 min).
    # Se compara contra user_sessions.last_activity_at.
    INACTIVITY_TIMEOUT_MINUTES: int = Field(default=30, gt=0)

    # --- CORS ---
    # Lista separada por comas; se usa como lista mediante `cors_origins_list`.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        # Variables del .env que no estén declaradas arriba se ignoran
        # (por ejemplo, una antigua BCRYPT_ROUNDS no rompe nada).
        extra="ignore",
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        """Impide arrancar con una clave débil o con el valor de ejemplo."""
        if len(value) < 32 or value.startswith("CAMBIAR"):
            raise ValueError(
                "SECRET_KEY debe tener al menos 32 caracteres y no puede ser el "
                "valor de ejemplo. Genera una con: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS convertido en lista (sin espacios ni vacíos)."""
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Crea la configuración una sola vez y reutiliza la misma instancia."""
    return Settings()


# Instancia lista para importar en todo el proyecto.
settings = get_settings()

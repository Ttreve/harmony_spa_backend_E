"""Conexión a MySQL: crea el `engine` de SQLAlchemy.

El engine es el "motor" que administra el pool de conexiones. Se crea una sola
vez al importar este módulo. La URL viene de DATABASE_URL (.env).
"""

from sqlalchemy import create_engine

from app.core.config import settings


def build_engine():
    # pool_pre_ping detecta conexiones MySQL que hayan quedado obsoletas.
    # Los parámetros de pool se mantienen moderados para el entorno inicial.
    return create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
    )


engine = build_engine()

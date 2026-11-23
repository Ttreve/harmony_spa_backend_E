"""Sesiones de base de datos.

- `SessionLocal`: fábrica de sesiones (se usa directo en scripts/).
- `get_db`: dependencia de FastAPI; entrega UNA sesión por petición HTTP y la
  cierra al terminar. Los endpoints la reciben con `Depends(get_db)`.
"""

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.database.connection import engine


SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,  # nada se envía a MySQL hasta flush/commit explícito
    autocommit=False,  # los cambios se confirman con db.commit()
    expire_on_commit=False,  # los objetos siguen usables después del commit
)


def get_db() -> Generator[Session, None, None]:
    """Entrega una sesión por solicitud y siempre la cierra."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

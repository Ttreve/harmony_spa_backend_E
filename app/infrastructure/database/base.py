from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Clase base de todos los modelos ORM de Harmony Spa.

    Todos los modelos (app/models/*.py) heredan de esta clase. SQLAlchemy usa
    `Base.metadata` para registrar tablas y relaciones, y Alembic lo consulta
    (migrations/env.py) para detectar cambios y generar migraciones.
    """

    pass

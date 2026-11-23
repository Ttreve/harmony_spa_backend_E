"""Configuración de Alembic (migraciones de la base de datos).

Alembic compara los modelos ORM (Base.metadata) con las tablas reales de MySQL
y genera/aplica migraciones. Comandos habituales (desde la raíz del proyecto):

    alembic revision --autogenerate -m "descripcion"   # generar migración
    alembic upgrade head                               # aplicarla
    alembic current / alembic history                  # consultar estado

La URL de conexión NO está en alembic.ini (allí hay un valor provisional):
se toma de DATABASE_URL en el archivo .env a través de `settings`.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.infrastructure.database.base import Base

# IMPORTANTE: importar los modelos para que queden registrados en
# Base.metadata. Si creas un modelo nuevo, agrégalo en app/models/__init__.py
# (este import ya carga todos los modelos listados allí).
import app.models  # noqa: F401  (registra TODAS las tablas en Base.metadata)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# La conexión real se obtiene desde las variables de entorno (.env).
# El "%" se duplica porque configparser lo usa como carácter especial.
config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace("%", "%%")
)

# Metadata que Alembic utilizará para comparar modelos y tablas.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Genera el SQL de la migración sin abrir una conexión directa."""

    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta las migraciones conectándose a la base de datos."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import URL

from database.models import Base


# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Metadata seluruh model Alfin dan Arza
target_metadata = Base.metadata


# ==========================================
# DATABASE CONNECTION
# ==========================================
def get_url() -> URL:
    return URL.create(
        "postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ["POSTGRES_HOST"],
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB"],
        query={
            "sslmode": os.getenv("POSTGRES_SSLMODE", "prefer")
        },
    )


# ==========================================
# AUTOGENERATE FILTER
# Melindungi tabel lama yang tidak didefinisikan
# dalam metadata model dari operasi penghapusan.
# ==========================================
def include_name(name, type_, parent_names):
    if type_ == "table":
        return name in target_metadata.tables

    return True


# ==========================================
# OFFLINE MIGRATION
# ==========================================
def run_migrations_offline() -> None:
    context.configure(
        url=get_url().render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_name=include_name,
    )

    with context.begin_transaction():
        context.run_migrations()


# ==========================================
# ONLINE MIGRATION
# ==========================================
def run_migrations_online() -> None:
    engine = create_engine(
        get_url(),
        poolclass=pool.NullPool,
    )

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_name=include_name,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

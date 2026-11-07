"""Ambiente do Alembic.

As migrações são escritas em SQL puro (op.execute); não há modelos ORM,
então o autogenerate não é usado.
"""
import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def url_do_banco() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "A variável DATABASE_URL não foi encontrada "
            "(defina no ambiente ou em backend/.env)."
        )
    # Usa o driver psycopg 3 (o mesmo dos scripts de ETL)
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def run_migrations_offline() -> None:
    context.configure(url=url_do_banco(), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(url_do_banco(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        # transaction_per_migration: cada migração é atômica por si só
        context.configure(connection=connection, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

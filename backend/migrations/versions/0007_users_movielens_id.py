"""Vínculo entre users e os usuários do MovieLens

Os 610 usuários do MovieLens viram contas em users (sem senha utilizável),
com o id original guardado em users.movielens_user_id. Os dados em si são
copiados por etl/migrar_usuarios_movielens.py.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS movielens_user_id integer;
        CREATE UNIQUE INDEX IF NOT EXISTS users_movielens_user_id_key
            ON users (movielens_user_id);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS users_movielens_user_id_key;
        ALTER TABLE users DROP COLUMN IF EXISTS movielens_user_id;
    """)

"""Gêneros preferidos do usuário (onboarding)

Usado no cold start: um usuário sem avaliações recebe os filmes populares
dos gêneros que escolheu no cadastro.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_genres (
            user_id integer NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            genre_id integer NOT NULL REFERENCES genres (id) ON DELETE CASCADE,
            PRIMARY KEY (user_id, genre_id)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_genres;")

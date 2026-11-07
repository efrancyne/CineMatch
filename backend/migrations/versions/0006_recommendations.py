"""Tabela de saída do recomendador

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            user_id integer NOT NULL REFERENCES users (id),
            movie_id integer NOT NULL REFERENCES movies (id),
            score float NOT NULL,
            rank integer NOT NULL,
            model_version varchar NOT NULL,
            generated_at timestamp NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, movie_id, model_version)
        );

        CREATE INDEX IF NOT EXISTS idx_recommendations_user_rank
            ON recommendations (user_id, model_version, rank);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS recommendations;")

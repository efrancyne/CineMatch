"""Controle do enriquecimento: movies.tmdb_checked_at

Marca quando o filme foi consultado no TMDB (com sucesso ou 404), para o
enriquecer_tmdb.py não reconsultar indefinidamente filmes que o TMDB não tem.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE movies ADD COLUMN IF NOT EXISTS tmdb_checked_at timestamp;")


def downgrade() -> None:
    op.execute("ALTER TABLE movies DROP COLUMN IF EXISTS tmdb_checked_at;")

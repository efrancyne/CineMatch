"""Índices para as consultas mais comuns

movies(tmdb_id) já é único desde a baseline (movies_tmdb_id_key).

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDICES = {
    "idx_ratings_movie_id": "ratings (movie_id)",
    "idx_follows_followed_user_id": "follows (followed_user_id)",
    "idx_comments_review_id": "comments (review_id)",
    "idx_likes_review_id": "likes (review_id)",
}


def upgrade() -> None:
    for nome, alvo in INDICES.items():
        op.execute(f"CREATE INDEX IF NOT EXISTS {nome} ON {alvo};")


def downgrade() -> None:
    for nome in INDICES:
        op.execute(f"DROP INDEX IF EXISTS {nome};")

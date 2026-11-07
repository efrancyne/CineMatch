"""Restrição: nota entre 0.5 e 5.0 em ratings

Antes de criar a constraint, verifica se algum dado existente a viola e,
nesse caso, aborta com uma mensagem clara (sem alterar nada).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$
        DECLARE
            violacoes integer;
        BEGIN
            SELECT count(*) INTO violacoes
            FROM ratings
            WHERE rating NOT BETWEEN 0.5 AND 5.0;

            IF violacoes > 0 THEN
                RAISE EXCEPTION
                    '% avaliações fora do intervalo 0.5–5.0; corrija antes de migrar.',
                    violacoes;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ratings_rating_check'
                  AND conrelid = 'ratings'::regclass
            ) THEN
                ALTER TABLE ratings
                    ADD CONSTRAINT ratings_rating_check
                    CHECK (rating BETWEEN 0.5 AND 5.0);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE ratings DROP CONSTRAINT IF EXISTS ratings_rating_check;")

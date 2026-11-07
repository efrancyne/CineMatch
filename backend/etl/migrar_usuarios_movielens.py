"""Cria contas em users para os usuários do MovieLens e copia as avaliações
de movielens_ratings (staging) para ratings.

- username/email fictícios (ml_user_N / ml_user_N@movielens.invalid);
- password_hash = '!' (marcador de senha inutilizável: ninguém faz login
  com essas contas);
- rated_at vem do timestamp Unix original, em UTC.

Idempotente: pode ser executado de novo sem duplicar nada.
Pré-requisito: migrações aplicadas (alembic upgrade head) e
importar_avaliacoes.py executado.
"""
import psycopg

from configuracao import database_url

with psycopg.connect(database_url()) as conexao:
    with conexao.cursor() as cursor:
        cursor.execute("""
            INSERT INTO users
                (username, name, email, password_hash, movielens_user_id)
            SELECT
                'ml_user_' || mr.movielens_user_id,
                'Usuário MovieLens ' || mr.movielens_user_id,
                'ml_user_' || mr.movielens_user_id || '@movielens.invalid',
                '!',
                mr.movielens_user_id
            FROM (SELECT DISTINCT movielens_user_id FROM movielens_ratings) mr
            -- NOT EXISTS (e não ON CONFLICT) para não gastar valores da
            -- sequence de users.id em reexecuções
            WHERE NOT EXISTS (
                SELECT 1 FROM users u
                WHERE u.movielens_user_id = mr.movielens_user_id
            )
            ORDER BY mr.movielens_user_id
        """)
        print(f"{cursor.rowcount} usuários do MovieLens criados.")

        cursor.execute("""
            INSERT INTO ratings (user_id, movie_id, rating, rated_at)
            SELECT
                u.id,
                mr.movie_id,
                mr.rating,
                to_timestamp(mr.timestamp_unix) AT TIME ZONE 'UTC'
            FROM movielens_ratings mr
            JOIN users u ON u.movielens_user_id = mr.movielens_user_id
            ON CONFLICT (user_id, movie_id) DO UPDATE
            SET rating = EXCLUDED.rating,
                rated_at = EXCLUDED.rated_at
            WHERE (ratings.rating, ratings.rated_at)
                  IS DISTINCT FROM (EXCLUDED.rating, EXCLUDED.rated_at)
        """)
        print(f"{cursor.rowcount} avaliações inseridas ou atualizadas.")

print("Migração dos usuários do MovieLens concluída.")

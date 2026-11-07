"""Fallback para usuários sem avaliações (cold start).

Popularidade por média bayesiana calculada direto no banco, opcionalmente
restrita a filmes de certos gêneros (onboarding: o usuário escolhe os
gêneros de que gosta). A API usa esta função quando o usuário não tem
linhas em recommendations.
"""
import psycopg
from psycopg.rows import tuple_row

# Número mínimo de votos da média bayesiana. Mais alto que no modelo de
# avaliação porque aqui a lista é a "vitrine" de um usuário novo: preferimos
# filmes consagrados a filmes com poucas notas altas.
VOTOS_MINIMOS = 20

SQL_POPULARES = """
    WITH estatisticas AS (
        SELECT movie_id, count(*) AS n, avg(rating) AS media
        FROM ratings
        GROUP BY movie_id
    ),
    global AS (
        SELECT avg(rating) AS c FROM ratings
    )
    SELECT e.movie_id,
           (e.n * e.media + %(m)s * g.c) / (e.n + %(m)s) AS score
    FROM estatisticas e
    CROSS JOIN global g
    WHERE (
        %(generos)s::text[] IS NULL
        OR EXISTS (
            SELECT 1
            FROM movie_genres mg
            JOIN genres gn ON gn.id = mg.genre_id
            WHERE mg.movie_id = e.movie_id
              AND gn.name = ANY(%(generos)s::text[])
        )
    )
      AND NOT (e.movie_id = ANY(%(excluir)s::int[]))
    ORDER BY score DESC, e.n DESC, e.movie_id
    LIMIT %(k)s
"""


def recomendar_cold_start(
    conexao: psycopg.Connection,
    k: int = 10,
    generos: list[str] | None = None,
    excluir: list[int] | None = None,
) -> list[tuple[int, float]]:
    """Top-k filmes populares e bem avaliados.

    generos: se informado, só filmes que tenham ao menos um desses gêneros
             (nomes como em genres.name, ex.: "Comedy").
    excluir: ids de filmes a não recomendar (ex.: já na watchlist).
    """
    # tuple_row: funciona mesmo se a conexão usar outro row_factory (a API usa dict_row)
    with conexao.cursor(row_factory=tuple_row) as cursor:
        cursor.execute(
            SQL_POPULARES,
            {
                "m": VOTOS_MINIMOS,
                "generos": generos or None,
                "excluir": excluir or [],
                "k": k,
            },
        )
        return [(int(movie_id), float(score)) for movie_id, score in cursor.fetchall()]

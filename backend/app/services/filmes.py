"""Consultas de filmes (só banco; nunca chama o TMDB)."""
import psycopg

from app.schemas import FilmeResumo, url_poster

# Colunas de resumo: gêneros e estatísticas via LATERAL (usa idx_ratings_movie_id)
_SELECT_RESUMO = """
    SELECT m.id, m.title, m.year, m.poster_path, m.overview, m.release_date,
           m.tmdb_id,
           COALESCE(gg.generos, '{}') AS generos,
           s.media, s.avaliacoes
    FROM movies m
    LEFT JOIN LATERAL (
        SELECT array_agg(g.name ORDER BY g.name) AS generos
        FROM movie_genres mg JOIN genres g ON g.id = mg.genre_id
        WHERE mg.movie_id = m.id
    ) gg ON true
    LEFT JOIN LATERAL (
        SELECT avg(r.rating)::float AS media, count(*) AS avaliacoes
        FROM ratings r WHERE r.movie_id = m.id
    ) s ON true
"""


def para_resumo(linha: dict) -> FilmeResumo:
    return FilmeResumo(
        id=linha["id"],
        title=linha["title"],
        year=linha["year"],
        poster_url=url_poster(linha["poster_path"]),
        generos=linha["generos"],
        media=round(linha["media"], 2) if linha["media"] is not None else None,
        avaliacoes=linha["avaliacoes"],
    )


def obter_linha(conexao: psycopg.Connection, movie_id: int) -> dict | None:
    return conexao.execute(_SELECT_RESUMO + " WHERE m.id = %s", (movie_id,)).fetchone()


def resumos(conexao: psycopg.Connection, ids: list[int]) -> dict[int, FilmeResumo]:
    """Resumo de vários filmes de uma vez, indexado por id."""
    if not ids:
        return {}
    linhas = conexao.execute(_SELECT_RESUMO + " WHERE m.id = ANY(%s)", (ids,)).fetchall()
    return {linha["id"]: para_resumo(linha) for linha in linhas}


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def buscar(
    conexao: psycopg.Connection,
    q: str | None,
    genero: str | None,
    pagina: int,
    tamanho: int,
) -> tuple[list[FilmeResumo], int]:
    filtros = """
        WHERE (%(q)s::text IS NULL OR m.title ILIKE %(padrao)s)
          AND (%(genero)s::text IS NULL OR EXISTS (
                SELECT 1 FROM movie_genres mg JOIN genres g ON g.id = mg.genre_id
                WHERE mg.movie_id = m.id AND lower(g.name) = lower(%(genero)s)))
    """
    params = {
        "q": q,
        "padrao": f"%{_escapar_like(q)}%" if q else None,
        "genero": genero,
        "limite": tamanho,
        "deslocamento": (pagina - 1) * tamanho,
    }
    total = conexao.execute("SELECT count(*) AS n FROM movies m " + filtros, params).fetchone()["n"]
    linhas = conexao.execute(
        _SELECT_RESUMO
        + filtros
        + " ORDER BY s.avaliacoes DESC, m.title, m.id LIMIT %(limite)s OFFSET %(deslocamento)s",
        params,
    ).fetchall()
    return [para_resumo(l) for l in linhas], total


def similares(conexao: psycopg.Connection, movie_id: int, k: int) -> list[tuple[int, float]]:
    """Filmes similares: primeiro por co-ocorrência de notas altas
    (cosseno entre os conjuntos de usuários que deram >= 4), completando
    com similaridade de gêneros (Jaccard) se faltar."""
    colaborativos = conexao.execute(
        """
        WITH alvo AS (
            SELECT user_id FROM ratings WHERE movie_id = %(id)s AND rating >= 4
        ),
        comum AS (
            SELECT r.movie_id, count(*) AS n
            FROM ratings r JOIN alvo USING (user_id)
            WHERE r.rating >= 4 AND r.movie_id <> %(id)s
            GROUP BY r.movie_id
            HAVING count(*) >= 2
        ),
        gostaram AS (
            SELECT movie_id, count(*) AS n
            FROM ratings
            WHERE rating >= 4 AND movie_id IN (SELECT movie_id FROM comum)
            GROUP BY movie_id
        )
        SELECT c.movie_id,
               c.n / sqrt(g.n::float * (SELECT count(*) FROM alvo)) AS score
        FROM comum c JOIN gostaram g USING (movie_id)
        ORDER BY score DESC, c.movie_id
        LIMIT %(k)s
        """,
        {"id": movie_id, "k": k},
    ).fetchall()
    resultado = [(l["movie_id"], float(l["score"])) for l in colaborativos]

    if len(resultado) < k:
        ja = [movie_id] + [m for m, _ in resultado]
        por_genero = conexao.execute(
            """
            WITH alvo AS (SELECT genre_id FROM movie_genres WHERE movie_id = %(id)s),
            n_alvo AS (SELECT count(*) AS n FROM alvo)
            SELECT mg.movie_id,
                   count(*) FILTER (WHERE mg.genre_id IN (SELECT genre_id FROM alvo))::float
                   / ((SELECT n FROM n_alvo) + count(*)
                      - count(*) FILTER (WHERE mg.genre_id IN (SELECT genre_id FROM alvo)))
                   AS jaccard,
                   (SELECT count(*) FROM ratings r WHERE r.movie_id = mg.movie_id) AS pop
            FROM movie_genres mg
            WHERE mg.movie_id <> ALL(%(ja)s)
            GROUP BY mg.movie_id
            HAVING count(*) FILTER (WHERE mg.genre_id IN (SELECT genre_id FROM alvo)) > 0
            ORDER BY jaccard DESC, pop DESC, mg.movie_id
            LIMIT %(faltam)s
            """,
            {"id": movie_id, "ja": ja, "faltam": k - len(resultado)},
        ).fetchall()
        # Score do fallback abaixo de qualquer colaborativo
        resultado += [(l["movie_id"], float(l["jaccard"]) * 0.01) for l in por_genero]
    return resultado

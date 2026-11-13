"""Recomendações: lê o lote pré-calculado (tabela recommendations) e, para
usuários sem linhas, usa o fallback de cold start (popularidade filtrada
pelos gêneros escolhidos no onboarding)."""
import psycopg

from app.schemas import Recomendacao, Recomendacoes
from app.services.filmes import resumos
from ml.cold_start import recomendar_cold_start


def para_usuario(conexao: psycopg.Connection, user_id: int, k: int) -> Recomendacoes:
    versao = conexao.execute(
        """
        SELECT model_version FROM recommendations
        WHERE user_id = %s
        ORDER BY generated_at DESC, model_version DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()

    pares: list[tuple[int, float]] = []
    if versao:
        # Ignora filmes que o usuário avaliou depois da geração do lote
        linhas = conexao.execute(
            """
            SELECT rec.movie_id, rec.score
            FROM recommendations rec
            WHERE rec.user_id = %(u)s AND rec.model_version = %(v)s
              AND NOT EXISTS (
                  SELECT 1 FROM ratings r
                  WHERE r.user_id = rec.user_id AND r.movie_id = rec.movie_id)
            ORDER BY rec.rank
            LIMIT %(k)s
            """,
            {"u": user_id, "v": versao["model_version"], "k": k},
        ).fetchall()
        pares = [(l["movie_id"], l["score"]) for l in linhas]

    if pares:
        fonte, model_version = "modelo", versao["model_version"]
    else:
        generos = [
            l["name"]
            for l in conexao.execute(
                """
                SELECT g.name FROM user_genres ug JOIN genres g ON g.id = ug.genre_id
                WHERE ug.user_id = %s
                """,
                (user_id,),
            ).fetchall()
        ]
        vistos = [
            l["movie_id"]
            for l in conexao.execute(
                "SELECT movie_id FROM ratings WHERE user_id = %s", (user_id,)
            ).fetchall()
        ]
        pares = recomendar_cold_start(conexao, k=k, generos=generos, excluir=vistos)
        fonte, model_version = "cold_start", None

    filmes = resumos(conexao, [m for m, _ in pares])
    return Recomendacoes(
        fonte=fonte,
        model_version=model_version,
        itens=[Recomendacao(filme=filmes[m], score=s) for m, s in pares if m in filmes],
    )


# Peso do "prior" da média bayesiana social: poucos votos de quem você segue
# puxam a nota para a média da comunidade em vez de dominar o ranking.
VOTOS_PRIOR_SOCIAL = 2


def social(
    conexao: psycopg.Connection,
    user_id: int,
    k: int,
    ranking: list[tuple[int, float]] | None = None,
) -> Recomendacoes:
    """Recomendação "para você" da home.

    Quem segue alguém: filmes que as pessoas seguidas avaliaram e o usuário
    ainda não viu, ordenados pela média bayesiana das notas delas. Se isso não
    preencher k itens (ou se não segue ninguém), completa/usa a comunidade
    inteira (popularidade bayesiana de todas as avaliações)."""
    seguidos = conexao.execute(
        "SELECT count(*) AS n FROM follows WHERE following_user_id = %s", (user_id,)
    ).fetchone()["n"]

    pares: list[tuple[int, float]] = []
    if seguidos:
        linhas = conexao.execute(
            """
            WITH global AS (SELECT avg(rating) AS c FROM ratings)
            SELECT r.movie_id,
                   (count(*) * avg(r.rating) + %(m)s * g.c) / (count(*) + %(m)s) AS score
            FROM ratings r
            JOIN follows f ON f.followed_user_id = r.user_id
                          AND f.following_user_id = %(u)s
            CROSS JOIN global g
            WHERE NOT EXISTS (
                SELECT 1 FROM ratings meu
                WHERE meu.user_id = %(u)s AND meu.movie_id = r.movie_id)
            GROUP BY r.movie_id, g.c
            ORDER BY score DESC, count(*) DESC, r.movie_id
            LIMIT %(k)s
            """,
            {"u": user_id, "m": VOTOS_PRIOR_SOCIAL, "k": k},
        ).fetchall()
        pares = [(l["movie_id"], float(l["score"])) for l in linhas]

    if len(pares) < k:
        excluir = [
            l["movie_id"]
            for l in conexao.execute(
                "SELECT movie_id FROM ratings WHERE user_id = %s", (user_id,)
            ).fetchall()
        ] + [m for m, _ in pares]
        if ranking is not None:  # ranking:top-rated vindo do Redis
            fora = set(excluir)
            pares += [(m, sc) for m, sc in ranking if m not in fora][: k - len(pares)]
        else:
            pares += recomendar_cold_start(conexao, k=k - len(pares), excluir=excluir)

    filmes = resumos(conexao, [m for m, _ in pares])
    return Recomendacoes(
        fonte="seguindo" if seguidos else "comunidade",
        model_version=None,
        itens=[Recomendacao(filme=filmes[m], score=s) for m, s in pares if m in filmes],
    )

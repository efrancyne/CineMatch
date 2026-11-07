"""Reviews, comentários e curtidas.

No schema, uma review é o texto ligado a uma avaliação (ratings.review_id):
o autor, o filme e a nota vêm da linha de ratings.
"""
import psycopg
from fastapi import HTTPException

from app.schemas import Comentario, ItemFeed, Review, ReviewDetalhe
from app.services.filmes import resumos
from app.services.usuarios import publico

_SELECT_REVIEW = """
    SELECT rv.id, rv.content, r.movie_id, r.rating, r.rated_at,
           u.id AS autor_id, u.username AS autor_username, u.name AS autor_name,
           u.bio AS autor_bio, u.avatar_url AS autor_avatar_url,
           (SELECT count(*) FROM likes l WHERE l.review_id = rv.id) AS curtidas,
           (SELECT count(*) FROM comments c WHERE c.review_id = rv.id) AS comentarios,
           EXISTS (SELECT 1 FROM likes l
                   WHERE l.review_id = rv.id AND l.user_id = %(viewer)s) AS curtida_por_mim
    FROM ratings r
    JOIN reviews rv ON rv.id = r.review_id
    JOIN users u ON u.id = r.user_id
"""

_FILTROS = """
    WHERE (%(movie_id)s::int IS NULL OR r.movie_id = %(movie_id)s)
      AND (%(user_id)s::int IS NULL OR r.user_id = %(user_id)s)
      AND (%(seguidor)s::int IS NULL OR r.user_id IN (
            SELECT followed_user_id FROM follows WHERE following_user_id = %(seguidor)s))
"""


def _para_review(linha: dict) -> Review:
    return Review(
        id=linha["id"],
        content=linha["content"],
        autor=publico(linha, "autor_"),
        movie_id=linha["movie_id"],
        rating=linha["rating"],
        rated_at=linha["rated_at"],
        curtidas=linha["curtidas"],
        comentarios=linha["comentarios"],
        curtida_por_mim=linha["curtida_por_mim"],
    )


def listar_reviews(
    conexao: psycopg.Connection,
    pagina: int,
    tamanho: int,
    movie_id: int | None = None,
    user_id: int | None = None,
    seguidor: int | None = None,
    viewer: int | None = None,
) -> tuple[list[Review], int]:
    params = {
        "movie_id": movie_id,
        "user_id": user_id,
        "seguidor": seguidor,
        "viewer": viewer,
        "limite": tamanho,
        "deslocamento": (pagina - 1) * tamanho,
    }
    total = conexao.execute(
        "SELECT count(*) AS n FROM ratings r JOIN reviews rv ON rv.id = r.review_id" + _FILTROS,
        params,
    ).fetchone()["n"]
    linhas = conexao.execute(
        _SELECT_REVIEW
        + _FILTROS
        + " ORDER BY r.rated_at DESC, rv.id DESC LIMIT %(limite)s OFFSET %(deslocamento)s",
        params,
    ).fetchall()
    return [_para_review(l) for l in linhas], total


def feed(conexao: psycopg.Connection, user_id: int, pagina: int, tamanho: int):
    """Reviews recentes de quem o usuário segue, com o resumo do filme."""
    reviews, total = listar_reviews(
        conexao, pagina, tamanho, seguidor=user_id, viewer=user_id
    )
    filmes = resumos(conexao, [r.movie_id for r in reviews])
    itens = [ItemFeed(**r.model_dump(), filme=filmes[r.movie_id]) for r in reviews]
    return itens, total


def obter_review(conexao: psycopg.Connection, review_id: int, viewer: int | None) -> ReviewDetalhe:
    linha = conexao.execute(
        _SELECT_REVIEW + " WHERE rv.id = %(id)s", {"id": review_id, "viewer": viewer}
    ).fetchone()
    if not linha:
        raise HTTPException(404, "Review não encontrada.")
    comentarios = conexao.execute(
        """
        SELECT c.id, c.review_id, c.content, c.created_at,
               u.id AS autor_id, u.username AS autor_username, u.name AS autor_name,
               u.bio AS autor_bio, u.avatar_url AS autor_avatar_url
        FROM comments c JOIN users u ON u.id = c.user_id
        WHERE c.review_id = %s
        ORDER BY c.created_at, c.id
        """,
        (review_id,),
    ).fetchall()
    return ReviewDetalhe(
        **_para_review(linha).model_dump(),
        lista_comentarios=[
            Comentario(
                id=c["id"],
                review_id=c["review_id"],
                autor=publico(c, "autor_"),
                content=c["content"],
                created_at=c["created_at"],
            )
            for c in comentarios
        ],
    )


def exigir_review(conexao: psycopg.Connection, review_id: int) -> None:
    if not conexao.execute("SELECT 1 FROM reviews WHERE id = %s", (review_id,)).fetchone():
        raise HTTPException(404, "Review não encontrada.")

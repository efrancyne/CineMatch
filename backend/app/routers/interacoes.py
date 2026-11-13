"""Ações do usuário autenticado: avaliar, favoritar, watchlist e seguir."""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Response, status

from app.deps import Conexao, Redis, exigir_filme, exigir_usuario
from app.schemas import Avaliacao, AvaliacaoEntrada
from app.security import UsuarioAtual
from app.services.cache import invalidar_recomendacoes

router = APIRouter(tags=["interações"])

def sem_conteudo() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/ratings", response_model=Avaliacao)
def avaliar(
    dados: AvaliacaoEntrada, conexao: Conexao, user_id: UsuarioAtual, r: Redis, tarefas: BackgroundTasks
):
    """Cria ou atualiza a nota do usuário para o filme. Se `review` vier
    preenchido, cria (ou atualiza) a review e a vincula, na mesma transação."""
    exigir_filme(conexao, dados.movie_id)
    linha = conexao.execute(
        """
        INSERT INTO ratings (user_id, movie_id, rating, rated_at)
        VALUES (%s, %s, %s, now())
        ON CONFLICT (user_id, movie_id) DO UPDATE
        SET rating = EXCLUDED.rating, rated_at = EXCLUDED.rated_at
        RETURNING user_id, movie_id, rating, rated_at, review_id
        """,
        (user_id, dados.movie_id, dados.rating),
    ).fetchone()

    texto = None
    if dados.review is not None:
        if linha["review_id"] is not None:
            conexao.execute(
                "UPDATE reviews SET content = %s WHERE id = %s",
                (dados.review, linha["review_id"]),
            )
        else:
            review_id = conexao.execute(
                "INSERT INTO reviews (content) VALUES (%s) RETURNING id", (dados.review,)
            ).fetchone()["id"]
            conexao.execute(
                "UPDATE ratings SET review_id = %s WHERE user_id = %s AND movie_id = %s",
                (review_id, user_id, dados.movie_id),
            )
            linha["review_id"] = review_id
        texto = dados.review
    elif linha["review_id"] is not None:
        texto = conexao.execute(
            "SELECT content FROM reviews WHERE id = %s", (linha["review_id"],)
        ).fetchone()["content"]

    tarefas.add_task(invalidar_recomendacoes, r, user_id)  # roda após o commit
    return Avaliacao(**linha, review=texto)


@router.delete("/ratings/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_avaliacao(
    movie_id: int, conexao: Conexao, user_id: UsuarioAtual, r: Redis, tarefas: BackgroundTasks
):
    """Remove a nota e, se houver, a review com seus comentários e curtidas."""
    linha = conexao.execute(
        "DELETE FROM ratings WHERE user_id = %s AND movie_id = %s RETURNING review_id",
        (user_id, movie_id),
    ).fetchone()
    if linha and linha["review_id"] is not None:
        rid = linha["review_id"]
        conexao.execute("DELETE FROM likes WHERE review_id = %s", (rid,))
        conexao.execute("DELETE FROM comments WHERE review_id = %s", (rid,))
        conexao.execute("DELETE FROM reviews WHERE id = %s", (rid,))
    tarefas.add_task(invalidar_recomendacoes, r, user_id)
    return sem_conteudo()


def _lista_de_filmes(tabela: str):
    """Gera os endpoints POST/DELETE idempotentes de favoritos e watchlist."""

    def adicionar(movie_id: int, conexao: Conexao, user_id: UsuarioAtual):
        exigir_filme(conexao, movie_id)
        conexao.execute(
            f"INSERT INTO {tabela} (user_id, movie_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (user_id, movie_id),
        )
        return sem_conteudo()

    def remover(movie_id: int, conexao: Conexao, user_id: UsuarioAtual):
        conexao.execute(
            f"DELETE FROM {tabela} WHERE user_id = %s AND movie_id = %s", (user_id, movie_id)
        )
        return sem_conteudo()

    return adicionar, remover


for caminho, tabela in (("favorites", "users_favorites"), ("watchlist", "watchlist")):
    adicionar, remover = _lista_de_filmes(tabela)
    router.add_api_route(
        f"/{caminho}/{{movie_id}}", adicionar, methods=["POST"],
        status_code=204, summary=f"Adiciona filme a {caminho}",
    )
    router.add_api_route(
        f"/{caminho}/{{movie_id}}", remover, methods=["DELETE"],
        status_code=204, summary=f"Remove filme de {caminho}",
    )


@router.post("/follows/{alvo_id}", status_code=status.HTTP_204_NO_CONTENT)
def seguir(
    alvo_id: int, conexao: Conexao, user_id: UsuarioAtual, r: Redis, tarefas: BackgroundTasks
):
    if alvo_id == user_id:
        raise HTTPException(422, "Não é possível seguir a si mesmo.")
    exigir_usuario(conexao, alvo_id)
    conexao.execute(
        """
        INSERT INTO follows (following_user_id, followed_user_id, created_at)
        VALUES (%s, %s, now()) ON CONFLICT DO NOTHING
        """,
        (user_id, alvo_id),
    )
    tarefas.add_task(invalidar_recomendacoes, r, user_id)
    return sem_conteudo()


@router.delete("/follows/{alvo_id}", status_code=status.HTTP_204_NO_CONTENT)
def deixar_de_seguir(
    alvo_id: int, conexao: Conexao, user_id: UsuarioAtual, r: Redis, tarefas: BackgroundTasks
):
    conexao.execute(
        "DELETE FROM follows WHERE following_user_id = %s AND followed_user_id = %s",
        (user_id, alvo_id),
    )
    tarefas.add_task(invalidar_recomendacoes, r, user_id)
    return sem_conteudo()

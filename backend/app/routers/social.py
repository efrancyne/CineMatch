"""Reviews, comentários e curtidas."""
from fastapi import APIRouter, HTTPException, Response, status

from app.deps import Conexao
from app.schemas import Comentario, ComentarioEntrada, ReviewDetalhe
from app.security import UsuarioAtual, UsuarioOpcional
from app.services.reviews import exigir_review, obter_review
from app.services.usuarios import COLUNAS_PUBLICAS, publico

router = APIRouter(tags=["social"])


@router.get("/reviews/{review_id}", response_model=ReviewDetalhe)
def detalhe_review(review_id: int, conexao: Conexao, viewer: UsuarioOpcional):
    return obter_review(conexao, review_id, viewer)


@router.post(
    "/reviews/{review_id}/comments",
    response_model=Comentario,
    status_code=status.HTTP_201_CREATED,
)
def comentar(review_id: int, dados: ComentarioEntrada, conexao: Conexao, user_id: UsuarioAtual):
    exigir_review(conexao, review_id)
    linha = conexao.execute(
        f"""
        WITH novo AS (
            INSERT INTO comments (review_id, user_id, content, created_at)
            VALUES (%s, %s, %s, now())
            RETURNING id, review_id, user_id, content, created_at
        )
        SELECT novo.id AS comentario_id, novo.review_id, novo.content, novo.created_at,
               {COLUNAS_PUBLICAS}
        FROM novo JOIN users u ON u.id = novo.user_id
        """,
        (review_id, user_id, dados.content),
    ).fetchone()
    return Comentario(
        id=linha["comentario_id"],
        review_id=linha["review_id"],
        autor=publico(linha),
        content=linha["content"],
        created_at=linha["created_at"],
    )


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_comentario(comment_id: int, conexao: Conexao, user_id: UsuarioAtual):
    """Só o autor do comentário pode apagá-lo."""
    linha = conexao.execute("SELECT user_id FROM comments WHERE id = %s", (comment_id,)).fetchone()
    if not linha:
        raise HTTPException(404, "Comentário não encontrado.")
    if linha["user_id"] != user_id:
        raise HTTPException(403, "Apenas o autor pode apagar o comentário.")
    conexao.execute("DELETE FROM comments WHERE id = %s", (comment_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reviews/{review_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def curtir(review_id: int, conexao: Conexao, user_id: UsuarioAtual):
    exigir_review(conexao, review_id)
    conexao.execute(
        """
        INSERT INTO likes (user_id, review_id, created_at)
        VALUES (%s, %s, now()) ON CONFLICT DO NOTHING
        """,
        (user_id, review_id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/reviews/{review_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def descurtir(review_id: int, conexao: Conexao, user_id: UsuarioAtual):
    conexao.execute(
        "DELETE FROM likes WHERE user_id = %s AND review_id = %s", (user_id, review_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

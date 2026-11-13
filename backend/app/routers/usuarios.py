from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool

from app.deps import Conexao, Pagina, Redis, Tamanho, exigir_filme, exigir_usuario
from app.schemas import (
    AtualizarPerfil,
    AvaliacaoComFilme,
    EstadoFilme,
    EstadoSeguir,
    FilmeResumo,
    GenerosEntrada,
    ItemFeed,
    Pagina as PaginaDe,
    Recomendacao,
    Recomendacoes,
    Review,
    UsuarioPerfil,
    UsuarioProprio,
    UsuarioPublico,
)
from app.security import UsuarioAtual, UsuarioOpcional
from app.services import cache
from app.services import recomendacoes as servico_recomendacoes
from app.services.filmes import resumos
from app.services.reviews import feed, listar_reviews
from app.services.usuarios import (
    COLUNAS_PUBLICAS,
    definir_generos,
    obter_perfil,
    obter_proprio,
    publico,
)

router = APIRouter(prefix="/users", tags=["usuários"])


# --- Rotas do próprio usuário (antes de /{user_id}) --------------------------

@router.get("/me/recommendations/social", response_model=Recomendacoes)
async def recomendacoes_sociais(
    conexao: Conexao,
    r: Redis,
    user_id: UsuarioAtual,
    k: Annotated[int, Query(ge=1, le=50)] = 10,
):
    """Recomendações da home: gosto de quem o usuário segue; sem seguidos (ou
    sem itens suficientes), completa com a comunidade inteira. Fica em cache
    no Redis (`recommendations:{user_id}`); avaliar ou seguir invalida."""
    em_cache = await cache.ler_recomendacoes(r, user_id, k)
    if em_cache is None:
        ranking = await cache.ranking_top_rated(r, conexao)
        calculado = await run_in_threadpool(
            servico_recomendacoes.social, conexao, user_id, cache.TAMANHO_RECOMENDACOES, ranking
        )
        await cache.gravar_recomendacoes(
            r, user_id, calculado.fonte, [(i.filme.id, i.score) for i in calculado.itens]
        )
        return Recomendacoes(fonte=calculado.fonte, model_version=None, itens=calculado.itens[:k])

    fonte, ids = em_cache
    filmes = await run_in_threadpool(resumos, conexao, ids)
    return Recomendacoes(
        fonte=fonte,
        model_version=None,
        # no cache o "score" é a posição; a nota da recomendação não é guardada
        itens=[Recomendacao(filme=filmes[m], score=float(len(ids) - i)) for i, m in enumerate(ids) if m in filmes],
    )


@router.get("/me", response_model=UsuarioProprio)
def eu(conexao: Conexao, user_id: UsuarioAtual):
    return obter_proprio(conexao, user_id)


@router.patch("/me", response_model=UsuarioProprio)
def atualizar_perfil(dados: AtualizarPerfil, conexao: Conexao, user_id: UsuarioAtual):
    campos = dados.model_dump(exclude_unset=True)
    if campos:
        atribuicoes = ", ".join(f"{c} = %({c})s" for c in campos)  # nomes vêm do schema
        conexao.execute(
            f"UPDATE users SET {atribuicoes} WHERE id = %(id)s", {**campos, "id": user_id}
        )
    return obter_proprio(conexao, user_id)


@router.put("/me/genres", response_model=UsuarioProprio)
def escolher_generos(dados: GenerosEntrada, conexao: Conexao, user_id: UsuarioAtual):
    """Onboarding: gêneros preferidos, usados nas recomendações de cold start."""
    definir_generos(conexao, user_id, dados.generos)
    return obter_proprio(conexao, user_id)


@router.get("/me/feed", response_model=PaginaDe[ItemFeed])
def meu_feed(conexao: Conexao, user_id: UsuarioAtual, pagina: Pagina = 1, tamanho: Tamanho = 20):
    """Reviews recentes de quem você segue."""
    itens, total = feed(conexao, user_id, pagina, tamanho)
    return PaginaDe[ItemFeed](itens=itens, total=total, pagina=pagina, tamanho=tamanho)


@router.get("/me/watchlist", response_model=PaginaDe[FilmeResumo])
def minha_watchlist(
    conexao: Conexao, user_id: UsuarioAtual, pagina: Pagina = 1, tamanho: Tamanho = 20
):
    return _filmes_da_lista(conexao, "watchlist", user_id, pagina, tamanho)


@router.get("/me/movies/{movie_id}", response_model=EstadoFilme)
def meu_estado_no_filme(movie_id: int, conexao: Conexao, user_id: UsuarioAtual):
    """Minha nota/review e se o filme está nos meus favoritos e na watchlist."""
    exigir_filme(conexao, movie_id)
    return conexao.execute(
        """
        SELECT r.rating AS nota, r.review_id, rv.content AS review,
               EXISTS (SELECT 1 FROM users_favorites f
                       WHERE f.user_id = %(u)s AND f.movie_id = %(m)s) AS favorito,
               EXISTS (SELECT 1 FROM watchlist w
                       WHERE w.user_id = %(u)s AND w.movie_id = %(m)s) AS watchlist
        FROM (SELECT 1) base
        LEFT JOIN ratings r ON r.user_id = %(u)s AND r.movie_id = %(m)s
        LEFT JOIN reviews rv ON rv.id = r.review_id
        """,
        {"u": user_id, "m": movie_id},
    ).fetchone()


@router.get("/me/following/{alvo_id}", response_model=EstadoSeguir)
def eu_sigo(alvo_id: int, conexao: Conexao, user_id: UsuarioAtual):
    linha = conexao.execute(
        "SELECT 1 FROM follows WHERE following_user_id = %s AND followed_user_id = %s",
        (user_id, alvo_id),
    ).fetchone()
    return {"seguindo": linha is not None}


# --- Perfis públicos ----------------------------------------------------------

@router.get("/{user_id}", response_model=UsuarioPerfil)
def perfil(user_id: int, conexao: Conexao):
    return obter_perfil(conexao, user_id)


@router.get("/{user_id}/ratings", response_model=PaginaDe[AvaliacaoComFilme])
def avaliacoes_do_usuario(
    user_id: int, conexao: Conexao, pagina: Pagina = 1, tamanho: Tamanho = 20
):
    exigir_usuario(conexao, user_id)
    total = conexao.execute(
        "SELECT count(*) AS n FROM ratings WHERE user_id = %s", (user_id,)
    ).fetchone()["n"]
    linhas = conexao.execute(
        """
        SELECT r.user_id, r.movie_id, r.rating, r.rated_at, r.review_id, rv.content AS review
        FROM ratings r LEFT JOIN reviews rv ON rv.id = r.review_id
        WHERE r.user_id = %s
        ORDER BY r.rated_at DESC, r.movie_id
        LIMIT %s OFFSET %s
        """,
        (user_id, tamanho, (pagina - 1) * tamanho),
    ).fetchall()
    filmes = resumos(conexao, [l["movie_id"] for l in linhas])
    itens = [AvaliacaoComFilme(**l, filme=filmes[l["movie_id"]]) for l in linhas]
    return PaginaDe[AvaliacaoComFilme](itens=itens, total=total, pagina=pagina, tamanho=tamanho)


@router.get("/{user_id}/reviews", response_model=PaginaDe[Review])
def reviews_do_usuario(
    user_id: int,
    conexao: Conexao,
    viewer: UsuarioOpcional,
    pagina: Pagina = 1,
    tamanho: Tamanho = 20,
):
    exigir_usuario(conexao, user_id)
    itens, total = listar_reviews(conexao, pagina, tamanho, user_id=user_id, viewer=viewer)
    return PaginaDe[Review](itens=itens, total=total, pagina=pagina, tamanho=tamanho)


@router.get("/{user_id}/favorites", response_model=PaginaDe[FilmeResumo])
def favoritos(user_id: int, conexao: Conexao, pagina: Pagina = 1, tamanho: Tamanho = 20):
    exigir_usuario(conexao, user_id)
    return _filmes_da_lista(conexao, "users_favorites", user_id, pagina, tamanho)


@router.get("/{user_id}/followers", response_model=PaginaDe[UsuarioPublico])
def seguidores(user_id: int, conexao: Conexao, pagina: Pagina = 1, tamanho: Tamanho = 20):
    return _pessoas(conexao, user_id, "followed_user_id", "following_user_id", pagina, tamanho)


@router.get("/{user_id}/following", response_model=PaginaDe[UsuarioPublico])
def seguindo(user_id: int, conexao: Conexao, pagina: Pagina = 1, tamanho: Tamanho = 20):
    return _pessoas(conexao, user_id, "following_user_id", "followed_user_id", pagina, tamanho)


@router.get("/{user_id}/recommendations", response_model=Recomendacoes)
def recomendacoes(
    user_id: int, conexao: Conexao, k: Annotated[int, Query(ge=1, le=50)] = 10
):
    """Top-k do lote mais recente do modelo; sem lote para o usuário, usa
    popularidade filtrada pelos gêneros escolhidos (cold start)."""
    exigir_usuario(conexao, user_id)
    return servico_recomendacoes.para_usuario(conexao, user_id, k)


# --- Auxiliares ---------------------------------------------------------------

def _filmes_da_lista(conexao, tabela: str, user_id: int, pagina: int, tamanho: int):
    # `tabela` só recebe valores fixos deste módulo
    total = conexao.execute(
        f"SELECT count(*) AS n FROM {tabela} WHERE user_id = %s", (user_id,)
    ).fetchone()["n"]
    ids = [
        l["movie_id"]
        for l in conexao.execute(
            f"SELECT movie_id FROM {tabela} WHERE user_id = %s ORDER BY movie_id LIMIT %s OFFSET %s",
            (user_id, tamanho, (pagina - 1) * tamanho),
        ).fetchall()
    ]
    filmes = resumos(conexao, ids)
    return PaginaDe[FilmeResumo](
        itens=[filmes[i] for i in ids], total=total, pagina=pagina, tamanho=tamanho
    )


def _pessoas(conexao, user_id: int, coluna_alvo: str, coluna_outro: str, pagina: int, tamanho: int):
    exigir_usuario(conexao, user_id)
    total = conexao.execute(
        f"SELECT count(*) AS n FROM follows WHERE {coluna_alvo} = %s", (user_id,)
    ).fetchone()["n"]
    linhas = conexao.execute(
        f"""
        SELECT {COLUNAS_PUBLICAS}
        FROM follows f JOIN users u ON u.id = f.{coluna_outro}
        WHERE f.{coluna_alvo} = %s
        ORDER BY f.created_at DESC NULLS LAST, u.id
        LIMIT %s OFFSET %s
        """,
        (user_id, tamanho, (pagina - 1) * tamanho),
    ).fetchall()
    return PaginaDe[UsuarioPublico](
        itens=[publico(l) for l in linhas], total=total, pagina=pagina, tamanho=tamanho
    )

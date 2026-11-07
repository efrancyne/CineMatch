import json
import logging
from typing import Annotated

import redis.asyncio as redis_async
from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from app.deps import Conexao, Config, Http, Pagina, Redis, Tamanho, exigir_filme
from app.schemas import FilmeDetalhe, FilmeResumo, Genero, Pagina as PaginaDe, Review
from app.security import UsuarioOpcional
from app.services import filmes as servico
from app.services.reviews import listar_reviews
from app.services.tmdb import detalhes_externos

log = logging.getLogger(__name__)
router = APIRouter(tags=["filmes"])

TTL_SIMILARES = 60 * 60


@router.get("/genres", response_model=list[Genero])
def listar_generos(conexao: Conexao):
    return conexao.execute("SELECT id, name FROM genres ORDER BY name").fetchall()


@router.get("/movies", response_model=PaginaDe[FilmeResumo])
def listar_filmes(
    conexao: Conexao,
    q: Annotated[str | None, Query(max_length=100, description="busca no título")] = None,
    genero: Annotated[str | None, Query(description="nome do gênero, ex.: Comedy")] = None,
    pagina: Pagina = 1,
    tamanho: Tamanho = 20,
):
    """Lista filmes (mais avaliados primeiro). Só dados do banco."""
    itens, total = servico.buscar(conexao, q or None, genero, pagina, tamanho)
    return PaginaDe[FilmeResumo](itens=itens, total=total, pagina=pagina, tamanho=tamanho)


@router.get("/movies/{movie_id}", response_model=FilmeDetalhe)
async def obter_filme(movie_id: int, conexao: Conexao, r: Redis, http: Http, settings: Config):
    """Dados do banco + detalhes do TMDB (elenco, diretor, keywords, vídeos)
    com cache no Redis. Se o TMDB falhar, `detalhes_externos` vem null."""
    linha = await run_in_threadpool(servico.obter_linha, conexao, movie_id)
    if not linha:
        raise HTTPException(404, "Filme não encontrado.")
    resumo = servico.para_resumo(linha)
    externos = await detalhes_externos(r, http, linha["tmdb_id"], settings)
    return FilmeDetalhe(
        **resumo.model_dump(),
        overview=linha["overview"],
        release_date=linha["release_date"],
        tmdb_id=linha["tmdb_id"],
        detalhes_externos=externos,
    )


@router.get("/movies/{movie_id}/similar", response_model=list[FilmeResumo])
async def filmes_similares(
    movie_id: int,
    conexao: Conexao,
    r: Redis,
    k: Annotated[int, Query(ge=1, le=50)] = 10,
):
    """Similares por co-avaliação (quem gostou deste também gostou de...),
    completados por gênero. Calculado na hora, com cache de 1 hora."""
    chave = f"similares:{movie_id}:{k}"
    ids = None
    try:
        em_cache = await r.get(chave)
        if em_cache is not None:
            ids = json.loads(em_cache)
    except redis_async.RedisError as erro:
        log.warning("Redis indisponível (similares): %s", erro)

    if ids is None:
        await run_in_threadpool(exigir_filme, conexao, movie_id)
        pares = await run_in_threadpool(servico.similares, conexao, movie_id, k)
        ids = [m for m, _ in pares]
        try:
            await r.set(chave, json.dumps(ids), ex=TTL_SIMILARES)
        except redis_async.RedisError as erro:
            log.warning("Redis indisponível (similares): %s", erro)

    filmes = await run_in_threadpool(servico.resumos, conexao, ids)
    return [filmes[m] for m in ids if m in filmes]


@router.get("/movies/{movie_id}/reviews", response_model=PaginaDe[Review])
def reviews_do_filme(
    movie_id: int,
    conexao: Conexao,
    viewer: UsuarioOpcional,
    pagina: Pagina = 1,
    tamanho: Tamanho = 20,
):
    exigir_filme(conexao, movie_id)
    itens, total = listar_reviews(conexao, pagina, tamanho, movie_id=movie_id, viewer=viewer)
    return PaginaDe[Review](itens=itens, total=total, pagina=pagina, tamanho=tamanho)

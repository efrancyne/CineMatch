"""Cache Redis das estruturas definidas no relatório (seção 2.4.2).

- ``ranking:top-rated``       Sorted Set  movie_id -> pontuação (média bayesiana)
- ``recommendations:{user}``  Sorted Set  movie_id -> posição (maior = mais recomendado)
- ``recommendations:{user}:fonte``  String  "seguindo" | "comunidade"

O cache é opcional: se o Redis cair, a API segue calculando direto no Postgres.
"""
import logging

import psycopg
import redis.asyncio as redis

from ml.cold_start import recomendar_cold_start

log = logging.getLogger("cinematch.cache")

CHAVE_RANKING = "ranking:top-rated"
TAMANHO_RANKING = 200
TTL_RANKING = 3600  # 1 hora
TTL_RECOMENDACOES = 600  # 10 minutos
TAMANHO_RECOMENDACOES = 50  # guarda o máximo aceito por `k`; o endpoint fatia


def chave_recomendacoes(user_id: int) -> str:
    return f"recommendations:{user_id}"


def _chave_fonte(user_id: int) -> str:
    return f"{chave_recomendacoes(user_id)}:fonte"


def calcular_ranking(conexao: psycopg.Connection) -> list[tuple[int, float]]:
    return recomendar_cold_start(conexao, k=TAMANHO_RANKING)


async def gravar_ranking(r: redis.Redis, pares: list[tuple[int, float]]) -> None:
    if not pares:
        return
    pipe = r.pipeline()
    pipe.delete(CHAVE_RANKING)
    pipe.zadd(CHAVE_RANKING, {str(m): s for m, s in pares})
    pipe.expire(CHAVE_RANKING, TTL_RANKING)
    await pipe.execute()


async def ranking_top_rated(
    r: redis.Redis, conexao: psycopg.Connection, calcular=calcular_ranking
) -> list[tuple[int, float]]:
    """Ranking geral, do mais bem avaliado ao menos. Cache-aside."""
    try:
        em_cache = await r.zrevrange(CHAVE_RANKING, 0, -1, withscores=True)
        if em_cache:
            return [(int(m), float(s)) for m, s in em_cache]
    except redis.RedisError as erro:
        log.warning("Redis indisponível (ranking): %s", erro)
    pares = calcular(conexao)
    try:
        await gravar_ranking(r, pares)
    except redis.RedisError as erro:
        log.warning("Redis indisponível (ranking): %s", erro)
    return pares


async def ler_recomendacoes(
    r: redis.Redis, user_id: int, k: int
) -> tuple[str, list[int]] | None:
    """(fonte, ids dos filmes em ordem) ou None se não há cache."""
    try:
        pares = await r.zrevrange(chave_recomendacoes(user_id), 0, k - 1)
        fonte = await r.get(_chave_fonte(user_id))
    except redis.RedisError as erro:
        log.warning("Redis indisponível (recomendações): %s", erro)
        return None
    if not pares or fonte is None:
        return None
    return fonte, [int(m) for m in pares]


async def gravar_recomendacoes(
    r: redis.Redis, user_id: int, fonte: str, pares: list[tuple[int, float]]
) -> None:
    if not pares:
        return
    chave = chave_recomendacoes(user_id)
    # A pontuação do Sorted Set é a posição na lista (n, n-1, ..., 1): preserva
    # exatamente a ordem calculada (quem você segue antes da comunidade) e evita empates.
    n = len(pares)
    try:
        pipe = r.pipeline()
        pipe.delete(chave)
        pipe.zadd(chave, {str(m): n - i for i, (m, _) in enumerate(pares)})
        pipe.expire(chave, TTL_RECOMENDACOES)
        pipe.set(_chave_fonte(user_id), fonte, ex=TTL_RECOMENDACOES)
        await pipe.execute()
    except redis.RedisError as erro:
        log.warning("Redis indisponível (recomendações): %s", erro)


async def invalidar_recomendacoes(r: redis.Redis, user_id: int) -> None:
    """Chamada quando o usuário avalia, remove nota ou segue/deixa de seguir."""
    try:
        await r.delete(chave_recomendacoes(user_id), _chave_fonte(user_id))
    except redis.RedisError as erro:
        log.warning("Redis indisponível ao invalidar: %s", erro)

"""Detalhes do TMDB (elenco, diretor, keywords, vídeos) com cache-aside no Redis.

Regras:
- Usado só na página do filme; listas nunca chamam o TMDB.
- Sucesso fica em cache por 7 dias; 404 ("o TMDB não tem") por 1 dia.
- Falhas (timeout, erro de rede, 429, 5xx) NÃO são cacheadas e não viram
  erro na API: o chamador recebe `Indisponivel` e responde só com o banco.
- Se o Redis estiver fora, segue direto para o TMDB (o cache é opcional).
- A chave da API nunca sai do backend.
"""
import json
import logging

import httpx
import redis.asyncio as redis

from app.config import Settings
from app.schemas import DetalhesExternos, Pessoa, Video

log = logging.getLogger(__name__)

TTL_SEGUNDOS = 60 * 60 * 24 * 7
TTL_NAO_ENCONTRADO = 60 * 60 * 24
URL_FOTO = "https://image.tmdb.org/t/p/w185"


class Indisponivel(Exception):
    """O TMDB não respondeu de forma utilizável (não é o mesmo que 404)."""


def chave_cache(tmdb_id: int) -> str:
    return f"tmdb:movie:{tmdb_id}:pt-BR"


async def detalhes_tmdb(
    r: redis.Redis,
    client: httpx.AsyncClient,
    tmdb_id: int,
    settings: Settings,
) -> dict | None:
    """JSON bruto do TMDB, ou None se o filme não existe lá (404).
    Levanta Indisponivel em caso de falha."""
    chave = chave_cache(tmdb_id)
    try:
        em_cache = await r.get(chave)
        if em_cache is not None:
            return json.loads(em_cache)  # pode ser None (404 cacheado)
    except redis.RedisError as erro:
        log.warning("Redis indisponível ao ler %s: %s", chave, erro)

    params = {"language": "pt-BR", "append_to_response": "credits,keywords,videos"}
    headers = {}
    if settings.tmdb_bearer_token:
        headers["Authorization"] = f"Bearer {settings.tmdb_bearer_token}"
    elif settings.tmdb_api_key:
        params["api_key"] = settings.tmdb_api_key
    else:
        raise Indisponivel("TMDB não configurado (sem token nem api_key).")

    try:
        resp = await client.get(
            f"{settings.tmdb_api_url}/movie/{tmdb_id}",
            params=params,
            headers=headers,
            timeout=settings.tmdb_timeout_segundos,
        )
    except httpx.HTTPError as erro:
        # Só o tipo do erro: a mensagem pode conter a URL com a api_key
        raise Indisponivel(f"falha de rede: {type(erro).__name__}") from None

    if resp.status_code == 404:
        await _gravar(r, chave, "null", TTL_NAO_ENCONTRADO)
        return None
    if resp.status_code != 200:
        raise Indisponivel(f"TMDB respondeu {resp.status_code}")

    dados = resp.json()
    await _gravar(r, chave, json.dumps(dados), TTL_SEGUNDOS)
    return dados


async def _gravar(r: redis.Redis, chave: str, valor: str, ttl: int) -> None:
    try:
        await r.set(chave, valor, ex=ttl)
    except redis.RedisError as erro:
        log.warning("Redis indisponível ao gravar %s: %s", chave, erro)


def extrair(dados: dict) -> DetalhesExternos:
    """Reduz o JSON do TMDB ao que a página do filme usa."""
    creditos = dados.get("credits") or {}
    elenco = [
        Pessoa(
            nome=p["name"],
            personagem=p.get("character") or None,
            foto_url=f"{URL_FOTO}{p['profile_path']}" if p.get("profile_path") else None,
        )
        for p in sorted(creditos.get("cast", []), key=lambda p: p.get("order", 999))[:10]
    ]
    diretores = [p["name"] for p in creditos.get("crew", []) if p.get("job") == "Director"]
    keywords = [k["name"] for k in (dados.get("keywords") or {}).get("keywords", [])]
    videos = [
        Video(nome=v.get("name", ""), tipo=v.get("type", ""), youtube_key=v["key"])
        for v in (dados.get("videos") or {}).get("results", [])
        if v.get("site") == "YouTube" and v.get("key")
    ]
    return DetalhesExternos(
        titulo_original=dados.get("original_title"),
        duracao_minutos=dados.get("runtime") or None,
        diretores=diretores,
        elenco=elenco,
        keywords=keywords,
        videos=videos,
    )


async def detalhes_externos(
    r: redis.Redis, client: httpx.AsyncClient, tmdb_id: int | None, settings: Settings
) -> DetalhesExternos | None:
    """Versão tolerante usada pela API: None em qualquer caso sem dados."""
    if tmdb_id is None:
        return None
    try:
        dados = await detalhes_tmdb(r, client, tmdb_id, settings)
    except Indisponivel as erro:
        log.warning("Detalhes do TMDB %s indisponíveis: %s", tmdb_id, erro)
        return None
    return extrair(dados) if dados is not None else None

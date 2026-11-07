"""Serviço do TMDB: cache hit, cache miss, 404 e falhas (com mock, sem rede)."""
import json

import pytest
import redis.asyncio as redis_async

from app.services.tmdb import chave_cache

pytestmark = pytest.mark.anyio


async def test_cache_miss_busca_no_tmdb_e_grava_no_redis(cliente, tmdb, redis_falso):
    resp = await cliente.get("/movies/1")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["overview"] == "Brinquedos ganham vida."  # do banco
    externos = corpo["detalhes_externos"]
    assert externos["diretores"] == ["John Lasseter"]
    assert [p["nome"] for p in externos["elenco"]] == ["Tom Hanks", "Tim Allen"]
    assert externos["elenco"][0]["foto_url"] == "https://image.tmdb.org/t/p/w185/tom.jpg"
    assert externos["keywords"] == ["toy"]
    assert externos["videos"] == [{"nome": "Trailer", "tipo": "Trailer", "youtube_key": "abc123"}]

    assert len(tmdb.chamadas) == 1
    req = tmdb.chamadas[0]
    assert req.url.path == "/3/movie/862"
    assert req.url.params["language"] == "pt-BR"
    assert req.url.params["append_to_response"] == "credits,keywords,videos"

    assert json.loads(await redis_falso.get(chave_cache(862)))["id"] == 862
    assert await redis_falso.ttl(chave_cache(862)) > 60 * 60 * 24 * 6


async def test_cache_hit_nao_chama_o_tmdb(cliente, tmdb):
    primeira = (await cliente.get("/movies/1")).json()
    segunda = (await cliente.get("/movies/1")).json()
    assert len(tmdb.chamadas) == 1
    assert primeira == segunda


async def test_404_do_tmdb_e_cacheado(cliente, tmdb, redis_falso):
    tmdb.modo = "404"
    resp = await cliente.get("/movies/2")
    assert resp.status_code == 200
    assert resp.json()["detalhes_externos"] is None
    assert await redis_falso.get(chave_cache(949)) == "null"
    assert 0 < await redis_falso.ttl(chave_cache(949)) <= 60 * 60 * 24

    await cliente.get("/movies/2")
    assert len(tmdb.chamadas) == 1  # o 404 veio do cache


@pytest.mark.parametrize("modo", ["rede", "500"])
async def test_falha_do_tmdb_nao_derruba_a_api_nem_e_cacheada(cliente, tmdb, redis_falso, modo):
    tmdb.modo = modo
    resp = await cliente.get("/movies/1")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["title"] == "Toy Story" and corpo["detalhes_externos"] is None
    assert await redis_falso.get(chave_cache(862)) is None

    # Quando o TMDB volta, a próxima requisição consegue os detalhes
    tmdb.modo = "ok"
    assert (await cliente.get("/movies/1")).json()["detalhes_externos"] is not None


async def test_filme_sem_tmdb_id_nao_chama_o_tmdb(cliente, tmdb):
    resp = await cliente.get("/movies/4")
    assert resp.status_code == 200
    assert resp.json()["detalhes_externos"] is None
    assert tmdb.chamadas == []


async def test_redis_fora_do_ar_nao_derruba_a_api(cliente, tmdb):
    from app.main import app

    app.state.redis = redis_async.Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.2)
    resp = await cliente.get("/movies/1")
    assert resp.status_code == 200
    assert resp.json()["detalhes_externos"]["diretores"] == ["John Lasseter"]
    assert len(tmdb.chamadas) == 1

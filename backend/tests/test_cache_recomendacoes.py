import pytest

from app.services import cache

pytestmark = pytest.mark.anyio


async def test_recomendacao_social_grava_sorted_set_no_redis(cliente, redis_falso, autenticar):
    headers = await autenticar("hugo")  # id 3, não segue ninguém
    corpo = (await cliente.get("/users/me/recommendations/social", headers=headers)).json()
    assert corpo["fonte"] == "comunidade" and corpo["itens"]

    guardados = await redis_falso.zrevrange("recommendations:3", 0, -1)
    assert [int(m) for m in guardados] == [i["filme"]["id"] for i in corpo["itens"]]
    assert await redis_falso.ttl("recommendations:3") > 0
    assert await redis_falso.exists(cache.CHAVE_RANKING)  # ranking:top-rated também foi gravado


async def test_segunda_chamada_vem_do_cache(cliente, redis_falso, autenticar, banco):
    headers = await autenticar("ivo")
    primeira = (await cliente.get("/users/me/recommendations/social", headers=headers)).json()
    with banco.connection() as conexao:  # muda o banco sem passar pela API
        conexao.execute("INSERT INTO ratings VALUES (3, 3, NULL, 5.0, now())")
    segunda = (await cliente.get("/users/me/recommendations/social", headers=headers)).json()
    ids = lambda c: [i["filme"]["id"] for i in c["itens"]]  # noqa: E731
    assert ids(segunda) == ids(primeira)  # a lista não foi recalculada


async def test_avaliar_e_seguir_invalidam_o_cache(cliente, redis_falso, autenticar):
    headers = await autenticar("jota")
    await cliente.get("/users/me/recommendations/social", headers=headers)
    assert await redis_falso.exists("recommendations:3")

    assert (await cliente.post("/ratings", json={"movie_id": 1, "rating": 4}, headers=headers)).status_code == 200
    assert not await redis_falso.exists("recommendations:3")

    await cliente.get("/users/me/recommendations/social", headers=headers)
    assert await redis_falso.exists("recommendations:3")
    assert (await cliente.post("/follows/2", headers=headers)).status_code == 204
    assert not await redis_falso.exists("recommendations:3")


async def test_sem_redis_a_api_continua_funcionando(cliente, autenticar, redis_falso):
    import redis.asyncio as redis

    async def quebrado(*a, **k):
        raise redis.ConnectionError("fora do ar")

    for metodo in ("zrevrange", "get", "pipeline", "delete"):
        setattr(redis_falso, metodo, quebrado) if metodo != "pipeline" else setattr(redis_falso, metodo, lambda *a, **k: (_ for _ in ()).throw(redis.ConnectionError("x")))
    headers = await autenticar("kaua")
    resp = await cliente.get("/users/me/recommendations/social", headers=headers)
    assert resp.status_code == 200 and resp.json()["itens"]

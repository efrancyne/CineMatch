import pytest

pytestmark = pytest.mark.anyio


async def test_usuario_com_historico_recebe_o_lote_do_modelo(cliente, tmdb):
    resp = await cliente.get("/users/1/recommendations", params={"k": 10})
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["fonte"] == "modelo" and corpo["model_version"] == "v-teste"
    assert [i["filme"]["title"] for i in corpo["itens"]] == ["Grumpier Old Men", "Up"]
    assert tmdb.chamadas == []  # recomendações usam só o banco


async def test_usa_a_versao_mais_recente_e_ignora_filmes_ja_avaliados(cliente, banco):
    with banco.connection() as conexao:
        conexao.execute("""
            INSERT INTO recommendations (user_id, movie_id, score, rank, model_version, generated_at)
            VALUES (1, 5, 0.7, 1, 'v-nova', now() + interval '1 hour'),
                   (1, 3, 0.6, 2, 'v-nova', now() + interval '1 hour')
        """)
        # Depois da geração, o usuário avaliou "Up"
        conexao.execute("INSERT INTO ratings VALUES (5, 1, NULL, 4.0, now())")
    corpo = (await cliente.get("/users/1/recommendations")).json()
    assert corpo["model_version"] == "v-nova"
    assert [i["filme"]["title"] for i in corpo["itens"]] == ["Grumpier Old Men"]


async def test_usuario_novo_recebe_cold_start_pelos_generos(cliente, autenticar):
    await autenticar("carla", generos=["Animation"])
    corpo = (await cliente.get("/users/3/recommendations")).json()
    assert corpo["fonte"] == "cold_start" and corpo["model_version"] is None
    assert corpo["itens"], "o cold start deveria devolver filmes"
    assert all("Animation" in i["filme"]["generos"] for i in corpo["itens"])


async def test_cold_start_sem_generos_e_sem_filmes_ja_vistos(cliente, autenticar):
    headers = await autenticar("davi")
    await cliente.post("/ratings", json={"movie_id": 1, "rating": 4}, headers=headers)
    corpo = (await cliente.get("/users/3/recommendations")).json()
    assert corpo["fonte"] == "cold_start"
    titulos = [i["filme"]["title"] for i in corpo["itens"]]
    assert "Toy Story" not in titulos and len(titulos) > 0


async def test_onboarding_altera_generos(cliente, autenticar):
    headers = await autenticar("eva")
    resp = await cliente.put("/users/me/genres", json={"generos": ["Drama"]}, headers=headers)
    assert resp.json()["generos"] == ["Drama"]
    corpo = (await cliente.get("/users/3/recommendations")).json()
    assert all("Drama" in i["filme"]["generos"] for i in corpo["itens"])


async def test_usuario_inexistente(cliente):
    assert (await cliente.get("/users/999/recommendations")).status_code == 404


async def test_home_sem_seguir_ninguem_usa_a_comunidade(cliente, autenticar):
    headers = await autenticar("fabi")
    corpo = (await cliente.get("/users/me/recommendations/social", headers=headers)).json()
    assert corpo["fonte"] == "comunidade"
    assert corpo["itens"], "a comunidade deveria render filmes"


async def test_home_com_seguidos_prioriza_o_gosto_deles(cliente, banco, autenticar):
    headers = await autenticar("gabi")  # id 3
    with banco.connection() as conexao:
        # o usuário 2 deu nota máxima ao filme 3 e baixa ao filme 4
        conexao.execute("DELETE FROM ratings WHERE user_id = 2")
        conexao.execute(
            "INSERT INTO ratings VALUES (3, 2, NULL, 5.0, now()), (4, 2, NULL, 1.0, now())"
        )
    assert (await cliente.post("/follows/2", headers=headers)).status_code == 204
    corpo = (await cliente.get("/users/me/recommendations/social", params={"k": 2}, headers=headers)).json()
    assert corpo["fonte"] == "seguindo"
    assert [i["filme"]["id"] for i in corpo["itens"]] == [3, 4]


async def test_home_exige_login(cliente):
    assert (await cliente.get("/users/me/recommendations/social")).status_code in (401, 403)

import pytest

pytestmark = pytest.mark.anyio


async def test_favoritos_e_watchlist_idempotentes(cliente, autenticar):
    headers = await autenticar()
    for _ in range(2):
        assert (await cliente.post("/favorites/1", headers=headers)).status_code == 204
        assert (await cliente.post("/watchlist/5", headers=headers)).status_code == 204

    favoritos = (await cliente.get("/users/3/favorites")).json()
    assert favoritos["total"] == 1 and favoritos["itens"][0]["title"] == "Toy Story"
    watchlist = (await cliente.get("/users/me/watchlist", headers=headers)).json()
    assert [f["title"] for f in watchlist["itens"]] == ["Up"]

    assert (await cliente.delete("/favorites/1", headers=headers)).status_code == 204
    assert (await cliente.get("/users/3/favorites")).json()["total"] == 0
    assert (await cliente.post("/favorites/9999", headers=headers)).status_code == 404


async def test_seguir_feed_curtir_e_comentar(cliente, autenticar):
    autora = await autenticar("autora")  # id 3
    leitor = await autenticar("leitor")  # id 4

    resp = await cliente.post(
        "/ratings", json={"movie_id": 5, "rating": 5, "review": "Emocionante."}, headers=autora
    )
    review_id = resp.json()["review_id"]

    # Seguir
    assert (await cliente.post("/follows/4", headers=leitor)).status_code == 422  # a si mesmo
    assert (await cliente.post("/follows/3", headers=leitor)).status_code == 204
    assert (await cliente.post("/follows/3", headers=leitor)).status_code == 204  # idempotente
    perfil = (await cliente.get("/users/3")).json()
    assert perfil["seguidores"] == 1 and perfil["avaliacoes"] == 1
    assert [u["username"] for u in (await cliente.get("/users/3/followers")).json()["itens"]] == ["leitor"]

    # Feed do leitor mostra a review da autora
    feed = (await cliente.get("/users/me/feed", headers=leitor)).json()
    assert feed["total"] == 1
    assert feed["itens"][0]["content"] == "Emocionante."
    assert feed["itens"][0]["filme"]["title"] == "Up"

    # Curtir (idempotente) e comentar
    for _ in range(2):
        assert (await cliente.post(f"/reviews/{review_id}/like", headers=leitor)).status_code == 204
    comentario = await cliente.post(
        f"/reviews/{review_id}/comments", json={"content": "Concordo!"}, headers=leitor
    )
    assert comentario.status_code == 201
    assert comentario.json()["autor"]["username"] == "leitor"

    detalhe = (await cliente.get(f"/reviews/{review_id}", headers=leitor)).json()
    assert detalhe["curtidas"] == 1 and detalhe["curtida_por_mim"] is True
    assert detalhe["comentarios"] == 1
    assert detalhe["lista_comentarios"][0]["content"] == "Concordo!"
    # Sem login, curtida_por_mim é falso
    assert (await cliente.get(f"/reviews/{review_id}")).json()["curtida_por_mim"] is False

    # Só o autor apaga o comentário
    cid = comentario.json()["id"]
    assert (await cliente.delete(f"/comments/{cid}", headers=autora)).status_code == 403
    assert (await cliente.delete(f"/comments/{cid}", headers=leitor)).status_code == 204

    # Descurtir e deixar de seguir
    assert (await cliente.delete(f"/reviews/{review_id}/like", headers=leitor)).status_code == 204
    assert (await cliente.delete("/follows/3", headers=leitor)).status_code == 204
    assert (await cliente.get("/users/me/feed", headers=leitor)).json()["total"] == 0


async def test_perfil_publico_nao_expoe_email_nem_senha(cliente, autenticar):
    await autenticar("discreta")
    perfil = (await cliente.get("/users/3")).json()
    assert "email" not in perfil and "password_hash" not in perfil


async def test_atualizar_perfil(cliente, autenticar):
    headers = await autenticar()
    resp = await cliente.patch("/users/me", json={"bio": "Cinéfila."}, headers=headers)
    assert resp.status_code == 200 and resp.json()["bio"] == "Cinéfila."
    assert resp.json()["name"] == "Ana"  # campo não enviado não muda


async def test_estado_do_usuario_no_filme_e_no_follow(cliente, autenticar):
    headers = await autenticar("estado")
    assert (await cliente.get("/users/me/movies/1")).status_code == 401
    vazio = (await cliente.get("/users/me/movies/1", headers=headers)).json()
    assert vazio == {"nota": None, "review_id": None, "review": None, "favorito": False, "watchlist": False}

    await cliente.post("/ratings", json={"movie_id": 1, "rating": 4.5, "review": "Bom"}, headers=headers)
    await cliente.post("/favorites/1", headers=headers)
    await cliente.post("/watchlist/1", headers=headers)
    estado = (await cliente.get("/users/me/movies/1", headers=headers)).json()
    assert estado["nota"] == 4.5 and estado["review"] == "Bom"
    assert estado["favorito"] is True and estado["watchlist"] is True
    assert (await cliente.get("/users/me/movies/9999", headers=headers)).status_code == 404

    outro = await autenticar("outro")
    alvo = (await cliente.get("/users/me", headers=outro)).json()["id"]
    assert (await cliente.get(f"/users/me/following/{alvo}", headers=headers)).json() == {"seguindo": False}
    await cliente.post(f"/follows/{alvo}", headers=headers)
    assert (await cliente.get(f"/users/me/following/{alvo}", headers=headers)).json() == {"seguindo": True}

import pytest

pytestmark = pytest.mark.anyio


async def test_cria_e_atualiza_a_mesma_avaliacao(cliente, autenticar):
    headers = await autenticar()
    criada = await cliente.post("/ratings", json={"movie_id": 2, "rating": 3.5}, headers=headers)
    assert criada.status_code == 200
    assert criada.json()["rating"] == 3.5 and criada.json()["review_id"] is None

    atualizada = await cliente.post("/ratings", json={"movie_id": 2, "rating": 4.5}, headers=headers)
    assert atualizada.status_code == 200
    assert atualizada.json()["rating"] == 4.5

    minhas = (await cliente.get("/users/3/ratings")).json()
    assert minhas["total"] == 1  # o mesmo par usuário/filme não duplicou
    assert minhas["itens"][0]["rating"] == 4.5
    assert minhas["itens"][0]["filme"]["title"] == "Heat"


@pytest.mark.parametrize("nota", [0, 0.3, 3.3, 5.5])
async def test_nota_invalida(cliente, autenticar, nota):
    headers = await autenticar()
    resp = await cliente.post("/ratings", json={"movie_id": 2, "rating": nota}, headers=headers)
    assert resp.status_code == 422


async def test_avaliar_exige_login_e_filme_existente(cliente, autenticar):
    assert (await cliente.post("/ratings", json={"movie_id": 2, "rating": 4})).status_code == 401
    headers = await autenticar()
    resp = await cliente.post("/ratings", json={"movie_id": 9999, "rating": 4}, headers=headers)
    assert resp.status_code == 404


async def test_review_criada_atualizada_e_removida_junto(cliente, autenticar):
    headers = await autenticar()
    resp = await cliente.post(
        "/ratings", json={"movie_id": 1, "rating": 5, "review": "Clássico!"}, headers=headers
    )
    review_id = resp.json()["review_id"]
    assert review_id is not None and resp.json()["review"] == "Clássico!"

    # Atualizar a nota sem texto mantém a review; com texto, edita a mesma
    resp = await cliente.post("/ratings", json={"movie_id": 1, "rating": 4.5}, headers=headers)
    assert resp.json()["review"] == "Clássico!"
    resp = await cliente.post(
        "/ratings", json={"movie_id": 1, "rating": 4.5, "review": "Muito bom."}, headers=headers
    )
    assert resp.json()["review_id"] == review_id

    reviews = (await cliente.get("/movies/1/reviews")).json()
    assert reviews["total"] == 1
    assert reviews["itens"][0]["content"] == "Muito bom."
    assert reviews["itens"][0]["rating"] == 4.5

    assert (await cliente.delete("/ratings/1", headers=headers)).status_code == 204
    assert (await cliente.get(f"/reviews/{review_id}")).status_code == 404
    assert (await cliente.get("/users/3/ratings")).json()["total"] == 0

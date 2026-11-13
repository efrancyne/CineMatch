import pytest

pytestmark = pytest.mark.anyio


async def test_lista_paginada_ordenada_por_popularidade(cliente, tmdb):
    resp = await cliente.get("/movies", params={"tamanho": 2})
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] == 5 and corpo["pagina"] == 1 and len(corpo["itens"]) == 2
    toy = corpo["itens"][0]
    assert toy["title"] == "Toy Story"  # mais avaliado (2 notas)
    assert toy["avaliacoes"] == 2 and toy["media"] == 4.5
    assert toy["generos"] == ["Animation", "Comedy"]
    assert toy["poster_url"] == "https://image.tmdb.org/t/p/w500/toy.jpg"

    pagina3 = (await cliente.get("/movies", params={"tamanho": 2, "pagina": 3})).json()
    assert len(pagina3["itens"]) == 1

    assert tmdb.chamadas == []  # listas nunca chamam o TMDB


async def test_busca_por_titulo_e_genero(cliente):
    por_titulo = (await cliente.get("/movies", params={"q": "toy"})).json()
    assert [f["title"] for f in por_titulo["itens"]] == ["Toy Story"]

    por_genero = (await cliente.get("/movies", params={"genero": "animation"})).json()
    assert {f["title"] for f in por_genero["itens"]} == {"Toy Story", "Up"}

    # Caracteres de LIKE são tratados literalmente
    assert (await cliente.get("/movies", params={"q": "%"})).json()["total"] == 0


async def test_generos(cliente):
    resp = await cliente.get("/genres")
    assert [g["name"] for g in resp.json()] == ["Animation", "Comedy", "Drama"]


async def test_filme_inexistente(cliente):
    resp = await cliente.get("/movies/9999")
    assert resp.status_code == 404
    assert resp.json()["erro"]["mensagem"] == "Filme não encontrado."


async def test_similares(cliente):
    resp = await cliente.get("/movies/1/similar", params={"k": 3})
    assert resp.status_code == 200
    titulos = [f["title"] for f in resp.json()]
    # Nenhum par tem 2+ usuários em comum com nota >= 4, então vale o
    # fallback por gênero: só filmes com algum gênero em comum (Animation/Comedy)
    assert set(titulos) == {"Grumpier Old Men", "Up"}
    # Cache: a segunda chamada devolve o mesmo resultado
    assert [f["title"] for f in (await cliente.get("/movies/1/similar", params={"k": 3})).json()] == titulos


async def test_filtros_por_ano_e_nota_minima(cliente):
    todos = (await cliente.get("/movies")).json()
    um_ano = todos["itens"][0]["year"]
    por_ano = (await cliente.get("/movies", params={"ano": um_ano})).json()
    assert por_ano["total"] >= 1
    assert all(f["year"] == um_ano for f in por_ano["itens"])

    # Toy Story tem média 4.5; só ele (e filmes com média >= 4.5) passam
    boas = (await cliente.get("/movies", params={"nota_minima": 4.5})).json()
    assert boas["total"] == len(boas["itens"]) >= 1
    assert all(f["media"] is not None and f["media"] >= 4.5 for f in boas["itens"])
    assert (await cliente.get("/movies", params={"nota_minima": 9})).status_code == 422

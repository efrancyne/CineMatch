import pytest

pytestmark = pytest.mark.anyio

NOVO = {
    "username": "bruna",
    "name": "Bruna",
    "email": "Bruna@Exemplo.com",
    "password": "senha-segura-123",
    "generos": ["Comedy", "drama"],
}


async def test_registro_nao_expoe_senha(cliente):
    resp = await cliente.post("/auth/register", json=NOVO)
    assert resp.status_code == 201
    corpo = resp.json()
    assert "password_hash" not in corpo and "password" not in corpo
    assert corpo["email"] == "bruna@exemplo.com"
    assert corpo["generos"] == ["Comedy", "Drama"]
    assert corpo["id"] == 3  # IDENTITY continua depois dos usuários existentes


async def test_registro_duplicado_retorna_409_no_formato_padrao(cliente):
    await cliente.post("/auth/register", json=NOVO)
    resp = await cliente.post("/auth/register", json={**NOVO, "username": "outra"})
    assert resp.status_code == 409
    assert resp.json() == {
        "erro": {"status": 409, "mensagem": "Username ou e-mail já cadastrado.", "detalhes": None}
    }


async def test_registro_com_genero_desconhecido(cliente):
    resp = await cliente.post("/auth/register", json={**NOVO, "generos": ["Faroeste Espacial"]})
    assert resp.status_code == 422
    # Nada foi gravado (a transação foi desfeita)
    login = await cliente.post("/auth/login", json={"username": "bruna", "password": NOVO["password"]})
    assert login.status_code == 401


async def test_validacao_retorna_detalhes(cliente):
    resp = await cliente.post("/auth/register", json={**NOVO, "password": "curta"})
    assert resp.status_code == 422
    erro = resp.json()["erro"]
    assert erro["mensagem"] == "Dados inválidos."
    assert any(d["campo"] == "body.password" for d in erro["detalhes"])


async def test_login_por_username_e_email_e_rota_protegida(cliente):
    await cliente.post("/auth/register", json=NOVO)
    for identificador in ("bruna", "bruna@exemplo.com"):
        resp = await cliente.post(
            "/auth/login", json={"username": identificador, "password": NOVO["password"]}
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]

    eu = await cliente.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert eu.status_code == 200
    assert eu.json()["username"] == "bruna"


async def test_login_com_senha_errada(cliente):
    await cliente.post("/auth/register", json=NOVO)
    resp = await cliente.post("/auth/login", json={"username": "bruna", "password": "errada-123"})
    assert resp.status_code == 401


async def test_usuario_do_movielens_nao_consegue_logar(cliente):
    resp = await cliente.post("/auth/login", json={"username": "ml_user_1", "password": "!"})
    assert resp.status_code == 401


async def test_sem_token_ou_token_invalido(cliente):
    assert (await cliente.get("/users/me")).status_code == 401
    resp = await cliente.get("/users/me", headers={"Authorization": "Bearer lixo"})
    assert resp.status_code == 401

"""Infraestrutura dos testes.

- Banco: `cinematch_test`, recriado a cada sessão pelas migrações do Alembic
  (no mesmo servidor do DATABASE_URL) e repovoado antes de cada teste.
- Redis: fakeredis em memória (um novo por teste).
- TMDB: httpx.MockTransport; nenhum teste chama a API real.
"""
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx
import psycopg
import pytest
from dotenv import load_dotenv

PASTA_BACKEND = Path(__file__).resolve().parent.parent
load_dotenv(PASTA_BACKEND / ".env")

NOME_BANCO_TESTE = "cinematch_test"


def _url_com_banco(url: str, banco: str) -> str:
    partes = urlsplit(url)
    return urlunsplit(partes._replace(path=f"/{banco}"))


URL_ORIGINAL = os.environ["DATABASE_URL"]
URL_TESTE = _url_com_banco(URL_ORIGINAL, NOME_BANCO_TESTE)

# Configura a API para os testes ANTES de importá-la
os.environ["DATABASE_URL"] = URL_TESTE
os.environ["TMDB_API_KEY"] = "chave-de-teste"
os.environ.pop("TMDB_BEARER_TOKEN", None)
os.environ.setdefault("JWT_SECRET", "segredo-de-teste-com-mais-de-16-caracteres")

from app.config import get_settings  # noqa: E402
from app.db import criar_pool  # noqa: E402
from app.main import app as aplicacao  # noqa: E402

get_settings.cache_clear()

DADOS_INICIAIS = """
    TRUNCATE recommendations, user_genres, likes, comments, follows,
             users_favorites, watchlist, ratings, reviews, movie_genres,
             movielens_ratings, movies, genres, users
             RESTART IDENTITY CASCADE;

    INSERT INTO genres (name) VALUES ('Animation'), ('Comedy'), ('Drama');

    INSERT INTO movies (title, year, movielens_id, tmdb_id, overview, poster_path) VALUES
        ('Toy Story', 1995, 1, 862, 'Brinquedos ganham vida.', '/toy.jpg'),
        ('Heat', 1995, 6, 949, 'Policial contra ladrão.', '/heat.jpg'),
        ('Grumpier Old Men', 1995, 3, 15602, NULL, NULL),
        ('Filme sem TMDB', 2001, 99, NULL, NULL, NULL),
        ('Up', 2009, 68954, 14160, 'Casa voadora.', '/up.jpg');

    INSERT INTO movie_genres (movie_id, genre_id) VALUES
        (1, 1), (1, 2), (2, 3), (3, 2), (4, 3), (5, 1);

    -- Usuários importados do MovieLens: senha inutilizável ('!')
    INSERT INTO users (username, name, email, password_hash, movielens_user_id) VALUES
        ('ml_user_1', 'Usuário MovieLens 1', 'ml_user_1@movielens.invalid', '!', 1),
        ('ml_user_2', 'Usuário MovieLens 2', 'ml_user_2@movielens.invalid', '!', 2);

    INSERT INTO ratings (user_id, movie_id, rating, rated_at) VALUES
        (1, 1, 5.0, '2018-01-01'), (1, 2, 4.0, '2018-01-02'),
        (2, 1, 4.0, '2018-01-01'), (2, 3, 5.0, '2018-01-03'), (2, 5, 4.5, '2018-01-04');

    INSERT INTO recommendations (user_id, movie_id, score, rank, model_version) VALUES
        (1, 3, 0.9, 1, 'v-teste'), (1, 5, 0.8, 2, 'v-teste');
"""


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def pool():
    """Recria o banco de teste a partir das migrações (uma vez por sessão)."""
    url_admin = _url_com_banco(URL_ORIGINAL, "postgres")
    with psycopg.connect(url_admin, autocommit=True) as admin:
        admin.execute(f"DROP DATABASE IF EXISTS {NOME_BANCO_TESTE} WITH (FORCE)")
        admin.execute(f"CREATE DATABASE {NOME_BANCO_TESTE}")

    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(PASTA_BACKEND / "alembic.ini")), "head")

    pool = criar_pool(URL_TESTE)
    yield pool
    pool.close()


@pytest.fixture
def banco(pool):
    """Dados conhecidos e IDs previsíveis em cada teste."""
    with pool.connection() as conexao:
        conexao.execute(DADOS_INICIAIS)
    return pool


class TmdbFalso:
    """Simula o TMDB. `modo`: "ok", "404", "500" ou "rede"."""

    def __init__(self):
        self.modo = "ok"
        self.chamadas: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.chamadas.append(request)
        if self.modo == "rede":
            raise httpx.ConnectError("falha simulada", request=request)
        if self.modo == "404":
            return httpx.Response(404, json={"status_message": "not found"})
        if self.modo == "500":
            return httpx.Response(500, json={})
        tmdb_id = int(request.url.path.rsplit("/", 1)[-1])
        return httpx.Response(200, json={
            "id": tmdb_id,
            "original_title": f"Original {tmdb_id}",
            "runtime": 81,
            "credits": {
                "cast": [
                    {"name": "Tom Hanks", "character": "Woody", "order": 0,
                     "profile_path": "/tom.jpg"},
                    {"name": "Tim Allen", "character": "Buzz", "order": 1},
                ],
                "crew": [
                    {"name": "John Lasseter", "job": "Director"},
                    {"name": "Fulano", "job": "Editor"},
                ],
            },
            "keywords": {"keywords": [{"id": 1, "name": "toy"}]},
            "videos": {"results": [
                {"name": "Trailer", "type": "Trailer", "site": "YouTube", "key": "abc123"},
                {"name": "Outro", "type": "Clip", "site": "Vimeo", "key": "x"},
            ]},
        })


@pytest.fixture
def tmdb():
    return TmdbFalso()


@pytest.fixture
def redis_falso():
    import fakeredis

    return fakeredis.FakeAsyncRedis(decode_responses=True)


@pytest.fixture
async def cliente(banco, tmdb, redis_falso):
    aplicacao.state.pool = banco
    aplicacao.state.redis = redis_falso
    aplicacao.state.http = httpx.AsyncClient(transport=httpx.MockTransport(tmdb))
    transporte = httpx.ASGITransport(app=aplicacao)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as c:
        yield c
    await aplicacao.state.http.aclose()


@pytest.fixture
def autenticar(cliente):
    """autenticar(username, generos) -> headers com o token de um usuário novo."""

    async def _autenticar(username="ana", generos=None):
        return await registrar_e_logar(cliente, username, generos)

    return _autenticar


async def registrar_e_logar(cliente, username="ana", generos=None) -> dict:
    """Cria um usuário e devolve os headers de autenticação."""
    resp = await cliente.post("/auth/register", json={
        "username": username,
        "name": username.title(),
        "email": f"{username}@exemplo.com",
        "password": "senha-segura-123",
        "generos": generos or [],
    })
    assert resp.status_code == 201, resp.text
    resp = await cliente.post(
        "/auth/login", json={"username": username, "password": "senha-segura-123"}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}

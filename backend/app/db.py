"""Acesso ao Postgres.

Usa psycopg síncrono com pool de conexões; os endpoints que consultam o
banco são funções `def` (o FastAPI as roda num threadpool). O psycopg
assíncrono não funciona com o event loop padrão do Windows, então esta
escolha mantém a API igual em qualquer sistema.
"""
from collections.abc import Iterator

import psycopg
from fastapi import Request
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def criar_pool(database_url: str) -> ConnectionPool:
    pool = ConnectionPool(
        database_url,
        min_size=1,
        max_size=10,
        kwargs={"row_factory": dict_row},
        open=False,
    )
    pool.open(wait=True, timeout=10)
    return pool


def get_conexao(request: Request) -> Iterator[psycopg.Connection]:
    """Dependência: uma conexão por requisição. Faz commit se o endpoint
    terminar sem erro e rollback se levantar exceção."""
    pool: ConnectionPool = request.app.state.pool
    with pool.connection() as conexao:
        yield conexao

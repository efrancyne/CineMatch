"""Dependências compartilhadas pelos routers."""
from typing import Annotated

import httpx
import psycopg
import redis.asyncio as redis
from fastapi import Depends, HTTPException, Query, Request

from app.config import Settings, get_settings
from app.db import get_conexao

Conexao = Annotated[psycopg.Connection, Depends(get_conexao)]
Config = Annotated[Settings, Depends(get_settings)]


def get_redis(request: Request) -> redis.Redis:
    return request.app.state.redis


def get_http(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


Redis = Annotated[redis.Redis, Depends(get_redis)]
Http = Annotated[httpx.AsyncClient, Depends(get_http)]

Pagina = Annotated[int, Query(ge=1, description="página (começa em 1)")]
Tamanho = Annotated[int, Query(ge=1, le=100, description="itens por página")]


def exigir_filme(conexao: psycopg.Connection, movie_id: int) -> None:
    if not conexao.execute("SELECT 1 FROM movies WHERE id = %s", (movie_id,)).fetchone():
        raise HTTPException(404, "Filme não encontrado.")


def exigir_usuario(conexao: psycopg.Connection, user_id: int) -> None:
    if not conexao.execute("SELECT 1 FROM users WHERE id = %s", (user_id,)).fetchone():
        raise HTTPException(404, "Usuário não encontrado.")

"""API do CineMatch.

Rodar (a partir de backend/):
    uvicorn app.main:app --reload
Documentação: http://localhost:8000/docs
"""
import logging
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import criar_pool
from app.erros import registrar_tratadores
from app.routers import auth, filmes, interacoes, social, usuarios

# O httpx registra a URL de cada requisição em INFO; com api_key na query
# isso vazaria a chave nos logs.
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cria os clientes uma única vez. Recursos já definidos em app.state
    (ex.: pelos testes) são mantidos e não são fechados aqui."""
    settings = get_settings()
    criados = []
    if not hasattr(app.state, "pool"):
        app.state.pool = criar_pool(settings.database_url)
        criados.append(app.state.pool.close)
    if not hasattr(app.state, "redis"):
        app.state.redis = redis.from_url(
            settings.redis_url, decode_responses=True, socket_timeout=2
        )
        criados.append(app.state.redis.aclose)
    if not hasattr(app.state, "http"):
        app.state.http = httpx.AsyncClient()
        criados.append(app.state.http.aclose)
    yield
    for fechar in reversed(criados):
        resultado = fechar()
        if hasattr(resultado, "__await__"):
            await resultado


def criar_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="CineMatch API",
        description="Rede social de filmes com recomendações personalizadas.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.lista_cors,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    registrar_tratadores(app)
    for modulo in (auth, usuarios, filmes, interacoes, social):
        app.include_router(modulo.router)

    @app.get("/health", tags=["infra"])
    def health():
        return {"status": "ok"}

    return app


app = criar_app()

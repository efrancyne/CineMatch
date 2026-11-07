"""Formato único para respostas de erro.

Toda resposta de erro tem o corpo:
    {"erro": {"status": 404, "mensagem": "...", "detalhes": [...] | null}}
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _resposta(status: int, mensagem: str, detalhes=None, headers=None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"erro": {"status": status, "mensagem": mensagem, "detalhes": detalhes}},
        headers=headers,
    )


def registrar_tratadores(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def erro_http(_: Request, exc: StarletteHTTPException):
        return _resposta(exc.status_code, str(exc.detail), headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def erro_validacao(_: Request, exc: RequestValidationError):
        detalhes = [
            {"campo": ".".join(str(p) for p in e["loc"]), "mensagem": e["msg"]}
            for e in exc.errors()
        ]
        return _resposta(422, "Dados inválidos.", detalhes)

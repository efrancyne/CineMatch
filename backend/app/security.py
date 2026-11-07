"""Hash de senha (Argon2) e tokens JWT."""
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.db import get_conexao

_hasher = PasswordHasher()
# Hash de uma senha qualquer, usado para gastar o mesmo tempo quando o
# usuário não existe (evita descobrir usernames pelo tempo de resposta).
_HASH_FICTICIO = _hasher.hash("senha-ficticia-para-tempo-constante")


def gerar_hash(senha: str) -> str:
    return _hasher.hash(senha)


def verificar_senha(senha: str, hash_salvo: str | None) -> bool:
    """False para senha errada, usuário inexistente (hash None) ou hash
    inutilizável (ex.: '!' dos usuários importados do MovieLens)."""
    try:
        return _hasher.verify(hash_salvo or _HASH_FICTICIO, senha) and hash_salvo is not None
    except (VerificationError, InvalidHashError):
        return False


def criar_token(user_id: int, settings: Settings) -> str:
    agora = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": agora,
        "exp": agora + timedelta(minutes=settings.jwt_expira_minutos),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algoritmo)


_bearer = HTTPBearer(auto_error=False)

_NAO_AUTENTICADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token ausente, inválido ou expirado.",
    headers={"WWW-Authenticate": "Bearer"},
)


def usuario_atual_id(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    conexao: Annotated[psycopg.Connection, Depends(get_conexao)],
) -> int:
    """Dependência: id do usuário autenticado (401 se não houver token válido)."""
    if credenciais is None:
        raise _NAO_AUTENTICADO
    try:
        payload = jwt.decode(
            credenciais.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algoritmo],
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _NAO_AUTENTICADO from None
    existe = conexao.execute("SELECT 1 FROM users WHERE id = %s", (user_id,)).fetchone()
    if not existe:
        raise _NAO_AUTENTICADO
    return user_id


def usuario_opcional_id(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    conexao: Annotated[psycopg.Connection, Depends(get_conexao)],
) -> int | None:
    """Dependência: id do usuário se houver token válido; None caso contrário
    (para endpoints públicos que mostram algo a mais a quem está logado)."""
    if credenciais is None:
        return None
    try:
        return usuario_atual_id(credenciais, settings, conexao)
    except HTTPException:
        return None


UsuarioAtual = Annotated[int, Depends(usuario_atual_id)]
UsuarioOpcional = Annotated[int | None, Depends(usuario_opcional_id)]

from fastapi import APIRouter, HTTPException, status
from psycopg import errors

from app.deps import Conexao, Config
from app.schemas import LoginEntrada, RegistroEntrada, Token, UsuarioProprio
from app.security import criar_token, gerar_hash, verificar_senha
from app.services.usuarios import definir_generos, obter_proprio

router = APIRouter(prefix="/auth", tags=["autenticação"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UsuarioProprio)
def registrar(dados: RegistroEntrada, conexao: Conexao):
    try:
        linha = conexao.execute(
            """
            INSERT INTO users (username, name, email, password_hash)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (dados.username, dados.name, dados.email.lower(), gerar_hash(dados.password)),
        ).fetchone()
    except errors.UniqueViolation:
        raise HTTPException(409, "Username ou e-mail já cadastrado.") from None
    definir_generos(conexao, linha["id"], dados.generos)
    return obter_proprio(conexao, linha["id"])


@router.post("/login", response_model=Token)
def login(dados: LoginEntrada, conexao: Conexao, settings: Config):
    linha = conexao.execute(
        "SELECT id, password_hash FROM users WHERE username = %s OR email = lower(%s)",
        (dados.username, dados.username),
    ).fetchone()
    if not verificar_senha(dados.password, linha["password_hash"] if linha else None):
        raise HTTPException(
            401, "Usuário ou senha incorretos.", headers={"WWW-Authenticate": "Bearer"}
        )
    return Token(access_token=criar_token(linha["id"], settings))

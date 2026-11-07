"""Consultas de usuários."""
import psycopg
from fastapi import HTTPException

from app.schemas import UsuarioPerfil, UsuarioProprio, UsuarioPublico

COLUNAS_PUBLICAS = "u.id, u.username, u.name, u.bio, u.avatar_url"


def publico(linha: dict, prefixo: str = "") -> UsuarioPublico:
    """Monta UsuarioPublico a partir de colunas (opcionalmente prefixadas,
    ex.: autor_id, autor_username...)."""
    return UsuarioPublico(
        id=linha[f"{prefixo}id"],
        username=linha[f"{prefixo}username"],
        name=linha[f"{prefixo}name"],
        bio=linha.get(f"{prefixo}bio"),
        avatar_url=linha.get(f"{prefixo}avatar_url"),
    )


def definir_generos(conexao: psycopg.Connection, user_id: int, generos: list[str]) -> None:
    """Substitui os gêneros preferidos. 422 se algum nome não existir."""
    nomes = sorted({g.strip() for g in generos if g.strip()})
    encontrados = conexao.execute(
        "SELECT id, name FROM genres WHERE lower(name) = ANY(%s)",
        ([n.lower() for n in nomes],),
    ).fetchall()
    if len(encontrados) != len(nomes):
        conhecidos = {l["name"].lower() for l in encontrados}
        faltando = [n for n in nomes if n.lower() not in conhecidos]
        raise HTTPException(422, f"Gêneros desconhecidos: {', '.join(faltando)}.")
    conexao.execute("DELETE FROM user_genres WHERE user_id = %s", (user_id,))
    for linha in encontrados:
        conexao.execute(
            "INSERT INTO user_genres (user_id, genre_id) VALUES (%s, %s)",
            (user_id, linha["id"]),
        )


def obter_proprio(conexao: psycopg.Connection, user_id: int) -> UsuarioProprio:
    linha = conexao.execute(
        f"""
        SELECT {COLUNAS_PUBLICAS}, u.email,
               COALESCE((SELECT array_agg(g.name ORDER BY g.name)
                         FROM user_genres ug JOIN genres g ON g.id = ug.genre_id
                         WHERE ug.user_id = u.id), '{{}}') AS generos
        FROM users u WHERE u.id = %s
        """,
        (user_id,),
    ).fetchone()
    return UsuarioProprio(**publico(linha).model_dump(), email=linha["email"], generos=linha["generos"])


def obter_perfil(conexao: psycopg.Connection, user_id: int) -> UsuarioPerfil:
    linha = conexao.execute(
        f"""
        SELECT {COLUNAS_PUBLICAS},
               (SELECT count(*) FROM ratings r WHERE r.user_id = u.id) AS avaliacoes,
               (SELECT count(*) FROM follows f WHERE f.followed_user_id = u.id) AS seguidores,
               (SELECT count(*) FROM follows f WHERE f.following_user_id = u.id) AS seguindo
        FROM users u WHERE u.id = %s
        """,
        (user_id,),
    ).fetchone()
    if not linha:
        raise HTTPException(404, "Usuário não encontrado.")
    return UsuarioPerfil(
        **publico(linha).model_dump(),
        avaliacoes=linha["avaliacoes"],
        seguidores=linha["seguidores"],
        seguindo=linha["seguindo"],
    )

"""Configuração compartilhada pelos scripts de ETL.

Lê o arquivo backend/.env (se existir); variáveis já definidas no
ambiente têm prioridade sobre as do arquivo.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

PASTA_BACKEND = Path(__file__).resolve().parent.parent
PASTA_DADOS = PASTA_BACKEND / "data" / "ml-latest-small"

load_dotenv(PASTA_BACKEND / ".env")


def variavel_obrigatoria(nome: str) -> str:
    valor = os.getenv(nome)
    if not valor:
        raise RuntimeError(
            f"A variável {nome} não foi encontrada. "
            "Defina-a no ambiente ou em backend/.env (veja .env.example)."
        )
    return valor


def database_url() -> str:
    return variavel_obrigatoria("DATABASE_URL")

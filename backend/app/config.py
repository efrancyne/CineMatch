"""Configuração da API, lida de variáveis de ambiente (ou backend/.env)."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ARQUIVO_ENV = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ARQUIVO_ENV, env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = Field(min_length=16)
    jwt_algoritmo: str = "HS256"
    jwt_expira_minutos: int = 60 * 24

    tmdb_api_url: str = "https://api.themoviedb.org/3"
    tmdb_bearer_token: str | None = None
    tmdb_api_key: str | None = None
    tmdb_timeout_segundos: float = 10.0

    # Origens permitidas no CORS, separadas por vírgula
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def lista_cors(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

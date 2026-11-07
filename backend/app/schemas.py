"""Modelos Pydantic de entrada e saída da API."""
from datetime import date, datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

T = TypeVar("T")

URL_POSTER = "https://image.tmdb.org/t/p/w500"


def url_poster(poster_path: str | None) -> str | None:
    return f"{URL_POSTER}{poster_path}" if poster_path else None


class Pagina(BaseModel, Generic[T]):
    itens: list[T]
    total: int
    pagina: int
    tamanho: int


# --- Autenticação e usuários -------------------------------------------------

Username = Annotated[str, Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_.]+$")]


class RegistroEntrada(BaseModel):
    username: Username
    name: Annotated[str, Field(min_length=1, max_length=100)]
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]
    generos: list[str] = Field(
        default_factory=list,
        description="Gêneros preferidos (onboarding), nomes como em GET /genres.",
    )


class LoginEntrada(BaseModel):
    username: str = Field(description="username ou e-mail")
    password: str


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UsuarioPublico(BaseModel):
    """Nunca inclui password_hash nem e-mail."""

    id: int
    username: str
    name: str
    bio: str | None = None
    avatar_url: str | None = None


class UsuarioPerfil(UsuarioPublico):
    avaliacoes: int
    seguidores: int
    seguindo: int


class UsuarioProprio(UsuarioPublico):
    email: str
    generos: list[str]


class AtualizarPerfil(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    bio: Annotated[str, Field(max_length=144)] | None = None
    avatar_url: Annotated[str, Field(max_length=500)] | None = None


class GenerosEntrada(BaseModel):
    generos: list[str]


# --- Filmes -------------------------------------------------------------------


class FilmeResumo(BaseModel):
    id: int
    title: str | None
    year: int | None
    poster_url: str | None
    generos: list[str]
    media: float | None = Field(description="média das notas (0.5–5)")
    avaliacoes: int


class Pessoa(BaseModel):
    nome: str
    personagem: str | None = None
    foto_url: str | None = None


class Video(BaseModel):
    nome: str
    tipo: str
    youtube_key: str


class DetalhesExternos(BaseModel):
    """Dados do TMDB (buscados sob demanda, em cache no Redis)."""

    titulo_original: str | None = None
    duracao_minutos: int | None = None
    diretores: list[str] = []
    elenco: list[Pessoa] = []
    keywords: list[str] = []
    videos: list[Video] = []


class FilmeDetalhe(FilmeResumo):
    overview: str | None
    release_date: date | None
    tmdb_id: int | None
    detalhes_externos: DetalhesExternos | None = Field(
        description="null se o filme não está no TMDB ou se o TMDB não respondeu"
    )


class Recomendacao(BaseModel):
    filme: FilmeResumo
    score: float


class Recomendacoes(BaseModel):
    fonte: Literal["modelo", "cold_start"]
    model_version: str | None
    itens: list[Recomendacao]


class Genero(BaseModel):
    id: int
    name: str


# --- Avaliações e reviews -----------------------------------------------------


class AvaliacaoEntrada(BaseModel):
    movie_id: int
    rating: float = Field(ge=0.5, le=5.0, description="0.5 a 5.0, de meio em meio ponto")
    review: Annotated[str, Field(min_length=1, max_length=250)] | None = Field(
        default=None, description="texto opcional da review (cria ou atualiza)"
    )

    @field_validator("rating")
    @classmethod
    def meio_ponto(cls, valor: float) -> float:
        if (valor * 2) != int(valor * 2):
            raise ValueError("a nota deve ser múltipla de 0.5")
        return valor


class Avaliacao(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    movie_id: int
    rating: float
    rated_at: datetime
    review_id: int | None = None
    review: str | None = None


class AvaliacaoComFilme(Avaliacao):
    filme: FilmeResumo


class Comentario(BaseModel):
    id: int
    review_id: int
    autor: UsuarioPublico
    content: str
    created_at: datetime


class ComentarioEntrada(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=144)]


class Review(BaseModel):
    id: int
    content: str
    autor: UsuarioPublico
    movie_id: int
    rating: float
    rated_at: datetime
    curtidas: int
    comentarios: int
    curtida_por_mim: bool = False


class ReviewDetalhe(Review):
    lista_comentarios: list[Comentario]


class ItemFeed(Review):
    filme: FilmeResumo


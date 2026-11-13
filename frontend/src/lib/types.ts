// Tipos espelhando backend/app/schemas.py

export interface Pagina<T> {
  itens: T[];
  total: number;
  pagina: number;
  tamanho: number;
}

export interface UsuarioPublico {
  id: number;
  username: string;
  name: string;
  bio: string | null;
  avatar_url: string | null;
}

export interface UsuarioProprio extends UsuarioPublico {
  email: string;
  generos: string[];
}

export interface FilmeResumo {
  id: number;
  title: string | null;
  year: number | null;
  poster_url: string | null;
  generos: string[];
  media: number | null;
  avaliacoes: number;
}

export interface Recomendacao {
  filme: FilmeResumo;
  score: number;
}

export interface Recomendacoes {
  fonte: "modelo" | "cold_start" | "seguindo" | "comunidade";
  model_version: string | null;
  itens: Recomendacao[];
}

export interface ItemFeed {
  id: number;
  content: string;
  autor: UsuarioPublico;
  movie_id: number;
  rating: number;
  rated_at: string;
  curtidas: number;
  comentarios: number;
  curtida_por_mim: boolean;
  filme: FilmeResumo;
}

export interface Token {
  access_token: string;
  token_type: "bearer";
}

export interface UsuarioPerfil extends UsuarioPublico {
  avaliacoes: number;
  seguidores: number;
  seguindo: number;
}

export interface Genero {
  id: number;
  name: string;
}

export interface Pessoa {
  nome: string;
  personagem: string | null;
  foto_url: string | null;
}

export interface Video {
  nome: string;
  tipo: string;
  youtube_key: string;
}

export interface DetalhesExternos {
  titulo_original: string | null;
  duracao_minutos: number | null;
  diretores: string[];
  elenco: Pessoa[];
  keywords: string[];
  videos: Video[];
}

export interface FilmeDetalhe extends FilmeResumo {
  overview: string | null;
  release_date: string | null;
  tmdb_id: number | null;
  detalhes_externos: DetalhesExternos | null;
}

export interface EstadoFilme {
  nota: number | null;
  review_id: number | null;
  review: string | null;
  favorito: boolean;
  watchlist: boolean;
}

export interface Review {
  id: number;
  content: string;
  autor: UsuarioPublico;
  movie_id: number;
  rating: number;
  rated_at: string;
  curtidas: number;
  comentarios: number;
  curtida_por_mim: boolean;
}

export interface Comentario {
  id: number;
  review_id: number;
  autor: UsuarioPublico;
  content: string;
  created_at: string;
}

export interface ReviewDetalhe extends Review {
  lista_comentarios: Comentario[];
}

export interface AvaliacaoComFilme {
  user_id: number;
  movie_id: number;
  rating: number;
  rated_at: string;
  review_id: number | null;
  review: string | null;
  filme: FilmeResumo;
}

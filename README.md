# CineMatch

O CineMatch é a combinação entre um sistema de recomendação e uma rede social, com possibilidade de interação entre os usuários. Os filmes foram carregados a partir do dataset MovieLens e informações visuais dos filmes foram obtidas através da API do TMDB.

- **Dados:** MovieLens `ml-latest-small` (610 usuários, 9.742 filmes, 100.836 avaliações).
- **TMDB:** fonte externa e complementar. O banco guarda só sinopse, data e pôster;
  elenco, diretor, keywords e vídeos são buscados sob demanda e ficam em cache no Redis.
- **Stack:** Python 3.14, PostgreSQL 16, Redis 7, FastAPI, Alembic, NumPy/SciPy/pandas;
  frontend em Next.js 16, React 19 e TypeScript (CSS Modules).

## Arquitetura

```
             ┌───────────────┐   HTTP/JSON    ┌──────────────────────────────┐
 frontend ──▶│  API FastAPI  │──────────────▶ │ TMDB (só na página do filme) │
             │  backend/app  │                └──────────────────────────────┘
             └──┬─────────┬──┘
     SQL (pool) │         │ cache (TMDB, similares, ranking, recomendações)
                ▼         ▼
        ┌────────────┐  ┌─────────┐
        │ PostgreSQL │  │  Redis  │  ← só cache: pode ser apagado sem perda
        └─────▲──────┘  └─────────┘
              │ lê ratings/gêneros e grava recommendations
   ┌──────────┴───────────┐        ┌───────────────────────────────┐
   │ backend/ml (lote)    │        │ backend/etl                   │
   │ avaliar → gerar_rec. │        │ MovieLens CSV → banco; TMDB → │
   └──────────────────────┘        │ sinopse/pôster                │
                                   └───────────────────────────────┘
```

O recomendador roda **em lote**: treina com os dados do banco e grava o top-50 de
cada usuário em `recommendations`; `GET /users/{id}/recommendations` só lê essa tabela. Para
usuários sem recomendações, usa um fallback de popularidade filtrada pelos gêneros que o
usuário escolheu no cadastro (cold start). Listas e buscas nunca chamam o TMDB.

O carrossel **"Recomendações para você"** do Home usa outro caminho, a **recomendação
social** (`GET /users/me/recommendations/social`), calculada na hora:

- quem segue alguém recebe os filmes que essas pessoas avaliaram e o usuário ainda não viu,
  ordenados pela média bayesiana das notas delas;
- quem não segue ninguém (ou quando faltam itens) recebe o que a **comunidade inteira** mais
  curte (`ranking:top-rated`).

O resultado fica no Redis (`recommendations:{user_id}`, 10 min) e é invalidado quando o
usuário avalia um filme ou segue/deixa de seguir alguém.

### Redis (somente cache)

| chave | tipo | TTL | conteúdo |
|---|---|---|---|
| `ranking:top-rated` | Sorted Set | 1 h | 200 filmes mais bem avaliados (média bayesiana) |
| `recommendations:{user_id}` | Sorted Set | 10 min | recomendação social (a pontuação é a posição na lista) |
| `recommendations:{user_id}:fonte` | String | 10 min | `seguindo` ou `comunidade` |
| `tmdb:movie:{tmdb_id}:pt-BR` | String (JSON) | 7 dias (404: 1 dia) | detalhes do TMDB |
| `similares:{movie_id}:{k}` | String (JSON) | 1 h | ids dos filmes similares |

Se o Redis cair, a API continua funcionando, direto do Postgres e do TMDB.

```
backend/
├── app/          API (routers/, services/, schemas.py, security.py, ...)
├── etl/          importação do MovieLens, enriquecimento pelo TMDB e dados sociais
├── ml/           modelos, métricas, avaliação, geração em lote, cold start
│   └── resultados/   tabela versionada de experimentos e EDA
├── migrations/   migrações Alembic (SQL puro)
├── tests/        testes da API (pytest)
├── data/         bd.sql (snapshot do schema), dataset e backups (ignorados no git)
├── compose.yaml  Postgres, Redis, pgAdmin e API
└── Dockerfile

frontend/         Next.js (src/app: rotas · src/components · src/lib: API, auth, hooks)
```

## Configuração

Todos os comandos abaixo rodam a partir de `backend/`.

1. Copie `.env.example` para `.env` e preencha. O `.env` nunca vai para o git.

   | variável | uso |
   |---|---|
   | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | criação do banco pelo compose |
   | `DATABASE_URL` | conexão usada pelos scripts e pela API (no host: `localhost`) |
   | `PGADMIN_EMAIL`, `PGADMIN_PASSWORD` | login do pgAdmin (http://localhost:5050) |
   | `TMDB_BEARER_TOKEN` ou `TMDB_API_KEY` | acesso ao TMDB (o token Bearer não aparece em URLs/logs) |
   | `REDIS_URL` | cache |
   | `JWT_SECRET` | assinatura dos tokens; gere com `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
   | `DEMO_PASSWORD` | senha do usuário de demonstração |
   | `CORS_ORIGINS` | origens do frontend, separadas por vírgula |

2. Ambiente Python local (para ETL, ML e testes):

   ```bash
   python -m venv ../.venv
   ../.venv/Scripts/activate        # Windows; no Linux/macOS: source ../.venv/bin/activate
   pip install -r requirements-dev.txt
   ```

3. Baixe o [MovieLens ml-latest-small](https://grouplens.org/datasets/movielens/latest/)
   e extraia em `backend/data/ml-latest-small/`.

> Rode o compose **sempre a partir de `backend/`**. O nome do projeto ("backend")
> define o volume do banco; rodar de outra pasta sobe um banco vazio.

## Subindo os serviços

```bash
docker compose up -d --build     # Postgres, Redis, pgAdmin e API
docker compose ps                # todos devem ficar "healthy"
```

A API fica em http://localhost:8000 e a documentação interativa em
http://localhost:8000/docs. Ela espera o Postgres e o Redis ficarem saudáveis
antes de iniciar.

## Banco: migrações

As migrações **não** rodam sozinhas ao subir a API. Faça backup antes de aplicá-las:

```bash
docker exec cinematch-postgres pg_dump -U cinematch -d cinematch -Fc > data/backups/antes.dump
alembic upgrade head                              # pelo host
# ou: docker compose run --rm api alembic upgrade head
```

Todas as migrações são idempotentes: a `0001_baseline` cria o schema completo
num banco vazio e não altera nada num banco que já o tem. O arquivo
`data/bd.sql` é só um snapshot; para regenerá-lo depois de uma migração:

```bash
docker exec cinematch-postgres pg_dump -s -U cinematch -d cinematch --no-owner \
  --no-privileges --exclude-table=alembic_version > data/bd.sql
```

## ETL (carga inicial)

Rode em ordem, a partir de `backend/etl/`. Todos os scripts podem ser reexecutados.

```bash
python importar_filmes.py             # movies, genres, movie_genres (+ tmdb_id do links.csv)
python importar_avaliacoes.py         # movielens_ratings (staging)
python migrar_usuarios_movielens.py   # 610 contas em users + avaliações em ratings
python enriquecer_tmdb.py --limite 20 # teste rápido; sem --limite processa todos
python popular_social.py              # reviews, follows, curtidas, comentários, favoritos e
                                      # watchlists fictícios (precisa do usuário demo, abaixo)
python gravar_ranking_redis.py        # ranking:top-rated inicial no Redis
```

O `enriquecer_tmdb.py` grava `tmdb_checked_at` e não reconsulta filmes já
checados (use `--refazer` para forçar). Ele também tenta de novo, com backoff,
em caso de erro de rede, 5xx ou 429, e termina com um resumo. Os usuários do
MovieLens têm senha inutilizável (`!`) e não fazem login. Para ter uma conta de
teste:

```bash
cd backend && python -m app.criar_usuario_demo   # usuário "demo", senha = DEMO_PASSWORD
```

Rode o `criar_usuario_demo` **antes** do `popular_social.py`: o script faz o `demo` seguir
usuários com reviews, para o feed não ficar vazio. O `popular_social.py` é determinístico
(semente fixa), só acrescenta dados e pode ser reexecutado. Ele dá nome, username e bio
realistas aos 150 usuários mais ativos do MovieLens e gera ≈1.800 reviews, ≈2,3 mil follows,
≈6,7 mil curtidas e ≈1,4 mil comentários. Os textos das reviews vêm de modelos de frase,
então se repetem entre filmes.

## Pipeline de recomendação

```bash
python -m ml.eda                    # estatísticas → ml/resultados/eda.md
python -m ml.avaliar                # treina e avalia todos os modelos → ml/resultados/
python -m ml.gerar_recomendacoes    # top-50 por usuário em recommendations
```

- **Split temporal por usuário:** as 20% avaliações mais recentes de cada usuário
  (no mínimo 1) vão para o teste. O split não é aleatório.
- **Relevante:** nota de teste ≥ 4.0. Filmes já vistos no treino não são recomendados.
- **Ajuste:** os fatores do SVD e o peso do híbrido são escolhidos por NDCG@10 numa
  validação temporal tirada **só do treino**. O teste não entra no ajuste.
- **Geração:** usa o modelo salvo em `ml/resultados/modelo_escolhido.json`, treinado com
  todas as avaliações. Reexecutar com a mesma `--versao` (padrão `hibrido-AAAA-MM-DD`)
  substitui só os registros dessa versão.
- `random_state` fixo em tudo que é aleatório.

### Resultados (K = 10, 592 usuários avaliados)

| modelo | Precision@10 | Recall@10 | NDCG@10 | MAP@10 | Cobertura@10 | Novidade@10 |
|---|---:|---:|---:|---:|---:|---:|
| aleatório | 0,0017 | 0,0007 | 0,0013 | 0,0003 | 0,462 | 7,32 |
| popularidade (contagem) | 0,0576 | 0,0484 | 0,0750 | 0,0359 | 0,010 | 1,52 |
| popularidade (média bayesiana) | 0,0098 | 0,0071 | 0,0194 | 0,0099 | 0,003 | 5,35 |
| item-item (cosseno, k=50) | 0,0807 | 0,0772 | 0,1010 | 0,0485 | 0,074 | 2,62 |
| SVD (50 fatores) | 0,0848 | 0,0875 | 0,1064 | 0,0492 | 0,069 | 2,51 |
| content-based (gêneros + década) | 0,0054 | 0,0030 | 0,0064 | 0,0022 | 0,356 | 7,10 |
| híbrido item-item + CB | 0,0868 | 0,0815 | 0,1087 | 0,0532 | 0,080 | 2,70 |
| híbrido SVD-50 + CB | 0,0863 | **0,0933** | 0,1110 | 0,0525 | 0,077 | 2,63 |
| **híbrido SVD-20 + CB (α=0,8), escolhido** | **0,0912** | 0,0866 | **0,1138** | **0,0557** | 0,055 | 2,36 |

O modelo escolhido tem o melhor NDCG@10 e supera os dois baselines: NDCG 52%
maior que a popularidade por contagem e cobertura do catálogo 5× maior. O
content-based sozinho é fraco no ranking, mas é o único que alcança filmes sem
avaliações, e no híbrido melhora o SVD. Tabela completa (K=10 e 20, com
diversidade) em [backend/ml/resultados/resultados.md](backend/ml/resultados/resultados.md).

## Frontend

Next.js 16 (App Router) + React 19 + TypeScript, com CSS Modules e a fonte Poppins.
Interface em português.

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local   # URL da API
npm run dev -- -p 3100                                         # http://localhost:3100
```

A origem do frontend precisa estar em `CORS_ORIGINS` do `backend/.env`
(ex.: `http://localhost:3100`). Antes, suba a API (`docker compose up -d`) e, para ter
conteúdo, rode o ETL.

| rota | tela |
|---|---|
| `/` | landing (redireciona logado para `/home`) |
| `/login`, `/cadastro` | autenticação (o cadastro inclui a escolha de gêneros) |
| `/home` | recomendações + feed de quem você segue |
| `/filmes/[id]` | detalhe, nota, favorito, watchlist, review e similares |
| `/buscar` | busca por título, gênero, ano e nota mínima |
| `/listas` | favoritos, watchlist e histórico |
| `/amigos` | seguindo e seguidores |
| `/usuarios/[id]` | perfil, seguir e editar o próprio perfil |
| `/reviews/[id]` | review com curtir, comentar e excluir |

Verificações: `npm run lint`, `npx tsc --noEmit` e `npm run build`.

## Testes

```bash
cd backend
pytest
```

São 46 testes. Eles criam um banco próprio (`cinematch_test`) pelas migrações,
no mesmo servidor do `DATABASE_URL`, e usam Redis falso (fakeredis) e TMDB
simulado (`httpx.MockTransport`), sem nenhuma chamada real ao TMDB. Cobrem:
- registro e login;
- busca e paginação de filmes;
- criação e atualização da mesma avaliação, e validação da nota;
- recomendações com e sem histórico, a recomendação social (comunidade e seguidos) e o cache dela
  no Redis (Sorted Set, acerto de cache, invalidação e API com o Redis fora do ar);
- o serviço do TMDB: cache hit, cache miss, 404, falha de rede, 5xx e Redis fora do ar;
- reviews, comentários, curtidas, follows, favoritos e watchlist.

## Endpoints

Rotas marcadas com 🔒 exigem `Authorization: Bearer <token>`. Erros sempre
vêm como `{"erro": {"status", "mensagem", "detalhes"}}`. Listas são paginadas
com `pagina` e `tamanho` (máx. 100) e respondem `{itens, total, pagina, tamanho}`.

| método | rota | descrição |
|---|---|---|
| POST | `/auth/register` | cadastro (com `generos` do onboarding) |
| POST | `/auth/login` | login por username ou e-mail → JWT |
| GET / PATCH 🔒 | `/users/me` | meus dados / editar nome, bio e avatar |
| PUT 🔒 | `/users/me/genres` | gêneros preferidos (cold start) |
| GET 🔒 | `/users/me/feed` | reviews de quem eu sigo |
| GET 🔒 | `/users/me/watchlist` | minha watchlist |
| GET 🔒 | `/users/me/movies/{id}` | meu estado num filme: nota, review, favorito, watchlist |
| GET 🔒 | `/users/me/following/{id}` | se eu sigo o usuário |
| GET 🔒 | `/users/me/recommendations/social?k=10` | recomendação do Home (`fonte`: `seguindo` ou `comunidade`) |
| GET | `/users/{id}` | perfil público com contadores |
| GET | `/users/{id}/ratings` · `/reviews` · `/favorites` | atividade do usuário |
| GET | `/users/{id}/followers` · `/following` | seguidores e seguidos |
| GET | `/users/{id}/recommendations?k=10` | recomendações do modelo em lote (`fonte`: `modelo` ou `cold_start`) |
| GET | `/genres` | lista de gêneros |
| GET | `/movies?q=&genero=&ano=&nota_minima=` | busca por título, gênero, ano e média mínima (só banco) |
| GET | `/movies/{id}` | detalhe + `detalhes_externos` do TMDB (null se indisponível) |
| GET | `/movies/{id}/similar?k=10` | similares (co-avaliação + gênero, com cache) |
| GET | `/movies/{id}/reviews` | reviews do filme |
| POST 🔒 | `/ratings` | cria/atualiza nota (0,5–5) e, opcionalmente, review |
| DELETE 🔒 | `/ratings/{movie_id}` | remove a nota e sua review |
| POST / DELETE 🔒 | `/favorites/{movie_id}` · `/watchlist/{movie_id}` | listas pessoais |
| POST / DELETE 🔒 | `/follows/{user_id}` | seguir / deixar de seguir |
| GET | `/reviews/{id}` | review com comentários |
| POST 🔒 | `/reviews/{id}/comments` | comentar |
| DELETE 🔒 | `/comments/{id}` | apagar o próprio comentário |
| POST / DELETE 🔒 | `/reviews/{id}/like` | curtir / descurtir |
| GET | `/health` | verificação de saúde |

Pôsteres: `poster_url` já vem pronto (`https://image.tmdb.org/t/p/w500` + `poster_path`).
A chave do TMDB nunca é enviada ao frontend.

## Decisões e observações

- **Usuários do MovieLens** viraram contas em `users` (`ml_user_N`), com o id original
  em `users.movielens_user_id`; os 150 mais ativos ganharam nome, username e bio pelo
  `popular_social.py` (mantêm o `movielens_user_id`). A tabela `movielens_ratings` fica como staging da importação.
- **Acesso síncrono ao banco** (psycopg + pool): no Windows, o psycopg assíncrono não
  funciona com o event loop padrão. Só o serviço do TMDB é assíncrono.
- **Os ids de `movies` não começam em 1** no banco atual (importações anteriores que
  falharam consumiram a sequence). Use sempre os ids que a API devolve.
- Experimentos são registrados numa tabela versionada (`ml/resultados/`), sem MLflow.
- **Nota de 0,5 a 5** (meias estrelas, como no MovieLens), garantida por `CHECK` no banco.

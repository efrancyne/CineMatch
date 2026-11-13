"""Povoa as tabelas sociais do CineMatch com dados fictícios (seção 2.7 do projeto).

O MovieLens não traz reviews, comentários, curtidas, follows, favoritos nem
watchlist, nem nomes de usuários. Este script gera um conjunto *reduzido* e
plausível desses dados, só para validar e demonstrar as funcionalidades:

- dá nome, username e bio realistas aos usuários mais ativos do MovieLens
  (os que mais avaliaram), mantendo `movielens_user_id`;
- escreve reviews em algumas das avaliações desses usuários e as coloca em
  datas recentes (a data original continua em `movielens_ratings`);
- cria follows, curtidas, comentários, favoritos e watchlists;
- faz o usuário `demo` seguir gente com reviews, para o feed não ficar vazio.

Só acrescenta dados: não apaga nada e não altera reviews já existentes.
Idempotente: se já houver reviews de contas do MovieLens, só completa a
cobertura de reviews dos filmes mais avaliados (e não repete o resto).
Determinístico (semente fixa). Pré-requisitos: migrações, ETL do MovieLens,
migrar_usuarios_movielens.py e `python -m app.criar_usuario_demo`.
"""
import random
import re
import unicodedata
from datetime import datetime, timedelta

import psycopg

from configuracao import database_url

SEMENTE = 2026
USUARIOS_ATIVOS = 150
SEGUIDOS_PELO_DEMO = 12
SEGUEM_O_DEMO = 8
FILMES_COM_COBERTURA = 400  # os mais avaliados...
REVIEWS_POR_FILME = 3       # ...ganham pelo menos esta quantidade de reviews

PRIMEIROS_NOMES = [
    "Maria", "João", "Ana", "Pedro", "Lucas", "Juliana", "Gabriel", "Beatriz", "Rafael", "Camila",
    "Mateus", "Larissa", "Felipe", "Letícia", "Bruno", "Amanda", "Thiago", "Fernanda", "Gustavo",
    "Isabela", "Rodrigo", "Mariana", "Diego", "Carolina", "Vinícius", "Natália", "Leonardo", "Bianca",
    "Eduardo", "Aline", "Henrique", "Patrícia", "Daniel", "Renata", "André", "Vanessa", "Marcelo",
    "Priscila", "Caio", "Débora", "Igor", "Tatiane", "Samuel", "Luana", "Otávio", "Raquel", "Yuri",
    "Elisa", "Davi", "Sofia", "Arthur", "Helena", "Murilo", "Clara", "Enzo", "Laura", "Ícaro", "Alice",
]
SOBRENOMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Costa", "Carvalho", "Almeida", "Ferreira",
    "Rodrigues", "Gomes", "Martins", "Araújo", "Ribeiro", "Barbosa", "Rocha", "Dias", "Nascimento",
    "Moreira", "Nunes", "Cardoso", "Teixeira", "Mendes", "Freitas", "Barros", "Pinto", "Moura", "Cavalcanti",
    "Monteiro", "Correia", "Batista", "Campos", "Duarte", "Fogaça", "Lopes", "Machado", "Azevedo",
]
BIOS = [
    "Cinéfilo de fim de semana.", "Filme bom é filme que a gente revê.", "Pipoca, sofá e boas histórias.",
    "Fã de ficção científica e de finais abertos.", "Procurando o próximo filme favorito.",
    "Maratonista de clássicos.", "Cinema nacional também é cinema!", "Terror só de dia, por favor.",
    "Trilha sonora importa tanto quanto o roteiro.", "Amante de cinema e café.", "Nolan, Villeneuve e Miyazaki.",
    "Comédia romântica sem culpa.", "Documentários e filmes de época.", "Assisto de tudo, menos filme ruim de propósito.",
    "Sempre no cinema na estreia.",
]

# Reviews por faixa de nota. {t} = título. Todas cabem em 250 caracteres.
REVIEWS = {
    "otimo": [
        "{t} é daqueles filmes que ficam na cabeça por dias. Roteiro afiado, atuações excelentes e um final que mexe com a gente.",
        "Obra-prima. {t} acerta em tudo: direção, trilha, fotografia. Já quero rever.",
        "Fui assistir sem expectativa e saí impressionado. {t} merece cada elogio que recebe.",
        "Que filme! {t} prende do primeiro ao último minuto. Recomendo sem pensar duas vezes.",
        "Rever {t} só confirma: continua incrível. Cada cena tem um motivo de existir.",
        "Nota máxima para {t}. Emocionante, bem conduzido e com personagens que a gente não esquece.",
    ],
    "bom": [
        "{t} é muito bom! Tem uns momentos mais lentos, mas o conjunto compensa bastante.",
        "Gostei bastante de {t}. Boa história, bom elenco e um final satisfatório.",
        "{t} entrega o que promete e ainda surpreende em alguns trechos. Vale a sessão.",
        "Filme sólido. {t} não reinventa nada, mas é muito bem feito e diverte do início ao fim.",
        "{t} me conquistou aos poucos. A segunda metade é bem melhor que a primeira.",
    ],
    "medio": [
        "{t} é ok. Tem boas ideias, mas não aproveita todo o potencial. Dá para assistir sem compromisso.",
        "Achei {t} mediano: bonito de ver, mas o roteiro se perde em alguns momentos.",
        "{t} começa bem e perde força no meio. Não é ruim, só não marcou.",
        "Esperava mais de {t}. Tem seus méritos, mas fiquei na vontade de algo mais ousado.",
    ],
    "fraco": [
        "{t} não funcionou para mim. Ritmo arrastado e personagens pouco interessantes.",
        "Não curti {t}. Boas intenções, execução fraca. Fica a lição: nem tudo que é famoso agrada.",
        "{t} decepcionou. O começo promete, mas o desenvolvimento é confuso e o final não convence.",
    ],
}
POR_GENERO = {
    "Comedy": "Rendeu boas risadas.", "Drama": "Tem cenas de arrepiar.", "Action": "As cenas de ação são ótimas.",
    "Horror": "A tensão não dá trégua.", "Romance": "Um romance que emociona de verdade.",
    "Sci-Fi": "A ambientação é muito bem pensada.", "Animation": "Serve para todas as idades.",
    "Thriller": "Cheio de reviravoltas.", "Crime": "Os diálogos são afiados.", "Adventure": "Uma aventura e tanto.",
    "Fantasy": "O universo criado é encantador.", "War": "Retrato duro e necessário.",
    "Mystery": "Fica difícil parar de teorizar.", "Documentary": "Informativo e envolvente.",
}
COMENTARIOS = [
    "Concordo totalmente!", "Também amei esse filme.", "Vou assistir no fim de semana, valeu pela dica!",
    "Boa review! Eu achei o final meio previsível, mas gostei bastante.", "Esse está na minha watchlist faz tempo.",
    "Discordo um pouco, mas respeito sua opinião 😄", "Que atuação incrível, né?", "Me deu vontade de rever agora.",
    "Uma das melhores trilhas sonoras que já ouvi.", "Deu curiosidade de assistir!", "Foi exatamente o que senti.",
    "Já vi três vezes e sempre descubro algo novo.", "Não esperava essa nota, mas faz sentido.",
    "Você me convenceu, vou colocar na lista.", "A fotografia é de outro mundo.", "Clássico absoluto.",
    "Achei superestimado, mas a sua review está ótima.", "Valeu pela recomendação!", "Esse final me pegou de surpresa.",
    "Também achei a segunda metade melhor.",
]


def ajustar_titulo(titulo: str) -> str:
    """'Shawshank Redemption, The' -> 'The Shawshank Redemption'."""
    achou = re.match(r"^(.*), (The|A|An|Les|La|Le|Il|Das|Der|Die)$", titulo)
    return f"{achou.group(2)} {achou.group(1)}" if achou else titulo


def texto_review(rng: random.Random, titulo: str, generos: list[str], nota: float) -> str:
    faixa = "otimo" if nota >= 4.5 else "bom" if nota >= 3.5 else "medio" if nota >= 2.5 else "fraco"
    t = ajustar_titulo(titulo)
    for _ in range(5):
        texto = rng.choice(REVIEWS[faixa]).format(t=t)
        extra = next((POR_GENERO[g] for g in generos if g in POR_GENERO), None)
        if extra and faixa in ("otimo", "bom") and rng.random() < 0.6:
            texto += " " + extra
        if len(texto) <= 250:
            return texto
        t = t[:60].rstrip() + "…"
    return texto[:250]


def slug(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", ".", sem_acento.lower()).strip(".")


def agora_menos(rng: random.Random, max_dias: int, min_dias: int = 0) -> datetime:
    return datetime.now().replace(microsecond=0) - timedelta(
        days=rng.uniform(min_dias, max_dias), hours=rng.randint(0, 23), minutes=rng.randint(0, 59)
    )


def completar_cobertura(cur, rng: random.Random) -> None:
    """Garante REVIEWS_POR_FILME reviews em cada um dos filmes mais avaliados,
    usando avaliações de usuários ativos que ainda não têm review."""
    cur.execute("""
        SELECT id FROM users
        WHERE movielens_user_id IS NOT NULL AND name NOT LIKE 'Usuário MovieLens %%'
    """)
    ativos = [linha[0] for linha in cur.fetchall()]
    cur.execute("""
        WITH top AS (
            SELECT movie_id FROM ratings GROUP BY movie_id ORDER BY count(*) DESC, movie_id LIMIT %s
        )
        SELECT t.movie_id, m.title,
               COALESCE((SELECT array_agg(g.name) FROM movie_genres mg
                         JOIN genres g ON g.id = mg.genre_id WHERE mg.movie_id = m.id), '{}'),
               (SELECT count(*) FROM ratings x WHERE x.movie_id = t.movie_id AND x.review_id IS NOT NULL)
        FROM top t JOIN movies m ON m.id = t.movie_id
    """, (FILMES_COM_COBERTURA,))
    filmes = [f for f in cur.fetchall() if f[3] < REVIEWS_POR_FILME]

    novas, curtidas, comentarios = 0, [], []
    for movie_id, titulo, generos, ja_tem in filmes:
        cur.execute(
            "SELECT user_id, rating FROM ratings WHERE movie_id = %s AND review_id IS NULL "
            "AND user_id = ANY(%s) ORDER BY user_id",
            (movie_id, ativos),
        )
        autores = cur.fetchall()
        for uid, nota in rng.sample(autores, min(len(autores), REVIEWS_POR_FILME - ja_tem)):
            cur.execute(
                "INSERT INTO reviews (content) VALUES (%s) RETURNING id",
                (texto_review(rng, titulo, generos, nota),),
            )
            rid = cur.fetchone()[0]
            cur.execute(
                "UPDATE ratings SET review_id = %s, rated_at = %s WHERE user_id = %s AND movie_id = %s",
                (rid, agora_menos(rng, 60), uid, movie_id),
            )
            novas += 1
            leitores = [u for u in ativos if u != uid]
            for leitor in rng.sample(leitores, rng.choice([0, 1, 2, 4, 7])):
                curtidas.append((leitor, rid, agora_menos(rng, 45)))
            if rng.random() < 0.3:
                for leitor in rng.sample(leitores, rng.randint(1, 3)):
                    comentarios.append((rid, leitor, rng.choice(COMENTARIOS), agora_menos(rng, 45)))
    cur.executemany(
        "INSERT INTO likes (user_id, review_id, created_at) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", curtidas
    )
    cur.executemany(
        "INSERT INTO comments (review_id, user_id, content, created_at) VALUES (%s, %s, %s, %s)", comentarios
    )
    print(f"Cobertura: {novas} reviews novas, {len(curtidas)} curtidas e {len(comentarios)} comentários "
          f"({len(filmes)} filmes populares estavam abaixo de {REVIEWS_POR_FILME} reviews).")


def main() -> None:
    rng = random.Random(SEMENTE)
    with psycopg.connect(database_url()) as conexao:
        cur = conexao.cursor()

        cur.execute("""
            SELECT count(*) FROM ratings r JOIN users u ON u.id = r.user_id
            WHERE r.review_id IS NOT NULL AND u.movielens_user_id IS NOT NULL
        """)
        if cur.fetchone()[0] > 0:
            print("Já existem reviews de contas do MovieLens; só completo a cobertura dos filmes populares.")
            completar_cobertura(cur, random.Random(SEMENTE + 1))
            return

        cur.execute("SELECT id FROM users WHERE username = 'demo'")
        demo = cur.fetchone()
        if not demo:
            raise SystemExit("Usuário 'demo' não encontrado. Rode: python -m app.criar_usuario_demo")
        demo_id = demo[0]

        # --- 1. usuários mais ativos ganham identidade ---------------------------
        cur.execute("""
            SELECT u.id FROM users u JOIN ratings r ON r.user_id = u.id
            WHERE u.movielens_user_id IS NOT NULL AND u.name LIKE 'Usuário MovieLens %%'
            GROUP BY u.id ORDER BY count(*) DESC, u.id LIMIT %s
        """, (USUARIOS_ATIVOS,))
        ativos = [linha[0] for linha in cur.fetchall()]
        if not ativos:
            raise SystemExit("Nenhum usuário do MovieLens disponível. Rode migrar_usuarios_movielens.py")

        cur.execute("SELECT username FROM users")
        usados = {linha[0] for linha in cur.fetchall()}
        combinacoes = [(p, s) for p in PRIMEIROS_NOMES for s in SOBRENOMES]
        rng.shuffle(combinacoes)
        for uid, (primeiro, sobrenome) in zip(ativos, combinacoes):
            base = f"{slug(primeiro)}.{slug(sobrenome)}"
            username, n = base, 1
            while username in usados:
                n += 1
                username = f"{base}{n}"
            usados.add(username)
            bio = rng.choice(BIOS) if rng.random() < 0.7 else None
            cur.execute(
                "UPDATE users SET name = %s, username = %s, bio = %s WHERE id = %s",
                (f"{primeiro} {sobrenome}", username, bio, uid),
            )
        print(f"{len(ativos)} usuários ativos com nome, username e bio.")

        # --- 2. reviews (e datas recentes) ---------------------------------------
        pessoas_review = ativos + [demo_id]
        cur.execute("""
            SELECT r.user_id, r.movie_id, r.rating, m.title,
                   COALESCE((SELECT array_agg(g.name) FROM movie_genres mg
                             JOIN genres g ON g.id = mg.genre_id WHERE mg.movie_id = m.id), '{}')
            FROM ratings r JOIN movies m ON m.id = r.movie_id
            WHERE r.user_id = ANY(%s) AND r.review_id IS NULL AND m.poster_path IS NOT NULL
            ORDER BY r.user_id, r.movie_id
        """, (pessoas_review,))
        candidatas: dict[int, list[tuple]] = {}
        for uid, movie_id, nota, titulo, generos in cur.fetchall():
            candidatas.setdefault(uid, []).append((movie_id, nota, titulo, generos))

        reviews_por_usuario: dict[int, int] = {}
        review_ids: list[tuple[int, int]] = []  # (review_id, autor)
        for uid in pessoas_review:
            lista = candidatas.get(uid, [])
            quantas = rng.randint(3, 4) if uid == demo_id else rng.randint(4, 9)
            for movie_id, nota, titulo, generos in rng.sample(lista, min(quantas, len(lista))):
                cur.execute(
                    "INSERT INTO reviews (content) VALUES (%s) RETURNING id",
                    (texto_review(rng, titulo, generos, nota),),
                )
                rid = cur.fetchone()[0]
                cur.execute(
                    "UPDATE ratings SET review_id = %s, rated_at = %s WHERE user_id = %s AND movie_id = %s",
                    (rid, agora_menos(rng, 60), uid, movie_id),
                )
                review_ids.append((rid, uid))
                reviews_por_usuario[uid] = reviews_por_usuario.get(uid, 0) + 1
        print(f"{len(review_ids)} reviews criadas.")

        # --- 3. follows ----------------------------------------------------------
        follows: set[tuple[int, int]] = set()
        for uid in ativos:
            for alvo in rng.sample([a for a in ativos if a != uid], rng.randint(5, 25)):
                follows.add((uid, alvo))
        mais_ativos_em_reviews = sorted(ativos, key=lambda u: (-reviews_por_usuario.get(u, 0), u))
        for alvo in mais_ativos_em_reviews[:SEGUIDOS_PELO_DEMO]:
            follows.add((demo_id, alvo))
        for uid in rng.sample(ativos, SEGUEM_O_DEMO):
            follows.add((uid, demo_id))
        cur.executemany(
            "INSERT INTO follows (following_user_id, followed_user_id, created_at) VALUES (%s, %s, %s) "
            "ON CONFLICT DO NOTHING",
            [(a, b, agora_menos(rng, 120)) for a, b in sorted(follows)],
        )
        print(f"{len(follows)} follows.")

        # --- 4. curtidas e comentários ------------------------------------------
        curtidas, comentarios = [], []
        for rid, autor in review_ids:
            leitores = [u for u in pessoas_review if u != autor]
            for leitor in rng.sample(leitores, min(len(leitores), rng.choice([0, 1, 2, 3, 4, 6, 9, 12]))):
                curtidas.append((leitor, rid, agora_menos(rng, 45)))
            if rng.random() < 0.35:
                for leitor in rng.sample(leitores, rng.randint(1, 4)):
                    comentarios.append((rid, leitor, rng.choice(COMENTARIOS), agora_menos(rng, 45)))
        cur.executemany(
            "INSERT INTO likes (user_id, review_id, created_at) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", curtidas
        )
        cur.executemany(
            "INSERT INTO comments (review_id, user_id, content, created_at) VALUES (%s, %s, %s, %s)", comentarios
        )
        print(f"{len(curtidas)} curtidas e {len(comentarios)} comentários.")

        # --- 5. favoritos e watchlist --------------------------------------------
        cur.execute("""
            SELECT movie_id FROM ratings GROUP BY movie_id ORDER BY count(*) DESC LIMIT 600
        """)
        populares = [linha[0] for linha in cur.fetchall()]
        favoritos, watchlist = 0, 0
        for uid in pessoas_review:
            cur.execute(
                "SELECT movie_id FROM ratings WHERE user_id = %s AND rating >= 4.5 ORDER BY movie_id", (uid,)
            )
            amados = [linha[0] for linha in cur.fetchall()]
            for movie_id in rng.sample(amados, min(len(amados), rng.randint(3, 8))):
                cur.execute(
                    "INSERT INTO users_favorites (user_id, movie_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (uid, movie_id),
                )
                favoritos += cur.rowcount
            cur.execute("SELECT movie_id FROM ratings WHERE user_id = %s", (uid,))
            vistos = {linha[0] for linha in cur.fetchall()}
            for movie_id in rng.sample([m for m in populares if m not in vistos], rng.randint(3, 8)):
                cur.execute(
                    "INSERT INTO watchlist (user_id, movie_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (uid, movie_id),
                )
                watchlist += cur.rowcount
        print(f"{favoritos} favoritos e {watchlist} itens de watchlist.")

        completar_cobertura(cur, rng)

    print("Povoamento social concluído.")


if __name__ == "__main__":
    main()

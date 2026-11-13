# CineMatch — frontend

Next.js 16 (App Router), React 19, TypeScript e CSS Modules. Consome a API FastAPI em `../backend`.

```bash
cp .env.example .env.local      # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev -- -p 3100          # a porta 3000 costuma estar em uso
npm run lint && npx tsc --noEmit && npm run build
```

O backend precisa estar no ar (`docker compose up -d` em `../backend`) e `http://localhost:3100`
deve constar em `CORS_ORIGINS` do `../backend/.env`.

Estrutura, rotas, convenções e pendências: veja [../HANDOFF.md](../HANDOFF.md).
Antes de usar APIs do Next, consulte `node_modules/next/dist/docs/` (veja `AGENTS.md`).

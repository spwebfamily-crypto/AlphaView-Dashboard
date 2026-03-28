# Deploy do Dashboard na Netlify

O `frontend` React/Vite pode ser publicado na Netlify. O `backend` FastAPI, o PostgreSQL e os workers continuam fora da Netlify.

## O que foi preparado no repositório

- `netlify.toml` na raiz para build de monorepo
- rewrite SPA para `index.html`
- proxy de `/api/*` já apontado para `https://alphaview-backend.onrender.com`
- build forçado em modo `PAPER`

## Como publicar na Netlify

1. Ligue o repositório à Netlify.
2. Deixe a Netlify ler o `netlify.toml` da raiz.
3. Faça o deploy.

O proxy `/api/*` já está configurado para o backend atual em `https://alphaview-backend.onrender.com`.

## Como hospedar o backend

O backend deve correr noutro serviço com Python + PostgreSQL, por exemplo `Render`, `Railway`, `Fly.io` ou VPS.

O frontend publicado na Netlify chama `/api/v1/*`. A Netlify recebe esse pedido e reencaminha para `https://alphaview-backend.onrender.com/api/v1/*`, o que mantém autenticação por cookie mais simples no browser.

## Variáveis mínimas do backend em produção

Use [backend/.env.netlify.example](C:/Users/Rodrigo🐐/OneDrive/Desktop/AlphaView-Dashboard/backend/.env.netlify.example) como base para as variáveis de produção.

As mais importantes são:

```env
APP_ENV=production
EXECUTION_MODE=PAPER
ENABLE_LIVE_TRADING=false
FRONTEND_BASE_URL=https://alphaview.netlify.app
BACKEND_CORS_ORIGINS=https://alphaview.netlify.app
AUTH_COOKIE_SECURE=true
EMAIL_DELIVERY_MODE=resend
RESEND_API_KEY=re_xxxxxxxxx
EMAIL_FROM_EMAIL=no-reply@yourdomain.com
DATABASE_URL=postgresql+psycopg://user:password@host:5432/alphaview
```

Se usar Stripe, alinhe também:

```env
STRIPE_CONNECT_RETURN_URL=https://alphaview.netlify.app/?stripe=return
STRIPE_CONNECT_REFRESH_URL=https://alphaview.netlify.app/?stripe=refresh
STRIPE_CHECKOUT_SUCCESS_URL=https://alphaview.netlify.app/?billing=success
STRIPE_CHECKOUT_CANCEL_URL=https://alphaview.netlify.app/?billing=cancel
STRIPE_BILLING_PORTAL_RETURN_URL=https://alphaview.netlify.app/?billing=portal
```

## Verificação rápida após o deploy

1. Abra o site publicado na Netlify.
2. Confirme que a página carrega em rota direta e em refresh.
3. Valide o proxy:

```text
https://alphaview.netlify.app/api/v1/health
```

4. Teste login, refresh de sessão e páginas que dependem da API.

## Limitações conhecidas

- A Netlify hospeda apenas o dashboard estático; não executa o FastAPI nem o PostgreSQL deste projeto.
- Se a URL pública do backend no Render mudar, será preciso atualizar `netlify.toml` e redeployar a Netlify.
- WebSockets live do Polygon não passam automaticamente por esta configuração estática da Netlify.

## Próximo passo recomendado

Adicionar um deploy de backend com Docker e variáveis de produção em `Render` ou `Railway`, para fechar o fluxo end-to-end de demo/paper trading.

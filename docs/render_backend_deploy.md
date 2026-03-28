# Deploy do Backend no Render

Este projeto jÃ¡ estÃ¡ preparado para subir o backend FastAPI no Render com Docker atravÃ©s de [render.yaml](C:/Users/RodrigoðŸ/OneDrive/Desktop/AlphaView-Dashboard/render.yaml).

## O que foi preparado

- `render.yaml` na raiz com:
  - `web service` Docker para o backend
  - `Render Postgres` gerido
  - `DATABASE_URL` ligado ao Postgres via Blueprint
  - `healthCheckPath` em `/api/v1/health`
  - `EXECUTION_MODE=PAPER`
  - `ENABLE_LIVE_TRADING=false`
- `Dockerfile` na raiz como fallback para o Render quando o serviÃ§o Docker Ã© criado fora do fluxo de Blueprint
- `infra/backend.Dockerfile` atualizado para respeitar a variÃ¡vel `PORT`
- [backend/.env.render.example](C:/Users/RodrigoðŸ/OneDrive/Desktop/AlphaView-Dashboard/backend/.env.render.example) com os overrides mÃ­nimos

## Como criar o backend no Render

1. FaÃ§a push do repositÃ³rio para GitHub.
2. No Render, escolha `New > Blueprint`.
3. Ligue o repositÃ³rio e selecione o ficheiro `render.yaml` da raiz.
4. O Blueprint jÃ¡ fica prÃ©-configurado com o frontend:

```env
FRONTEND_BASE_URL=https://alphaview.netlify.app
BACKEND_CORS_ORIGINS=https://alphaview.netlify.app
```

Se o domÃ­nio do frontend mudar no futuro, ajuste esses dois valores no Render.

5. Confirme a criaÃ§Ã£o do serviÃ§o `alphaview-backend` e da base de dados `alphaview-db`.

Se vocÃª jÃ¡ tiver criado um `Web Service` normal em vez de `Blueprint`, o repositÃ³rio agora tambÃ©m funciona nesse modo porque o Render encontrarÃ¡ o `Dockerfile` na raiz por defeito.

## O que o Render vai criar

- um web service pÃºblico para o FastAPI
- uma base de dados Postgres gratuita

O serviÃ§o usa `Docker`, faz health check em:

```text
/api/v1/health
```

e liga ao Postgres com a `connectionString` privada do prÃ³prio Render.

## VariÃ¡veis importantes

Estas variÃ¡veis jÃ¡ ficam definidas pelo `render.yaml`:

```env
APP_ENV=production
EXECUTION_MODE=PAPER
ENABLE_LIVE_TRADING=false
AUTH_COOKIE_SECURE=true
ALLOW_PUBLIC_REGISTRATION=true
PORT=10000
```

Estas precisam ser definidas no Render:

```env
FRONTEND_BASE_URL=https://alphaview.netlify.app
BACKEND_CORS_ORIGINS=https://alphaview.netlify.app
```

VariÃ¡veis opcionais que vocÃª pode acrescentar depois, se precisar:

```env
POLYGON_API_KEY=
EODHD_API_TOKEN=
STRIPE_PUBLISHABLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
```

## Como ligar com a Netlify

Depois do primeiro deploy do backend, copie a URL pÃºblica do Render, por exemplo:

```text
https://alphaview-backend.onrender.com
```

e configure na Netlify:

```env
NETLIFY_API_ORIGIN=https://alphaview-backend.onrender.com
```

## Como verificar

1. Abra `https://SEU-BACKEND.onrender.com/api/v1/health`
2. Confirme resposta `200`
3. Abra o frontend na Netlify
4. Teste o proxy `/api/v1/health`


## LimitaÃ§Ãµes conhecidas

- O plano gratuito do Render faz o web service entrar em idle apÃ³s inatividade.
- O Postgres gratuito expira `30 dias` apÃ³s a criaÃ§Ã£o.
- O arranque da aplicaÃ§Ã£o ainda cria o schema de forma bootstrap-style; nÃ£o hÃ¡ Alembic neste milestone.

## PrÃ³ximo passo recomendado

Adicionar um worker/cron no Render para backfill, feature materialization e retraining, em vez de deixar esses processos apenas para execuÃ§Ã£o manual.


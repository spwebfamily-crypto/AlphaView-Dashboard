# Deploy do Backend no Render

Este projeto já está preparado para subir o backend FastAPI no Render com Docker através de [render.yaml](C:/Users/Rodrigo🐐/OneDrive/Desktop/AlphaView-Dashboard/render.yaml).

## O que foi preparado

- `render.yaml` na raiz com:
  - `web service` Docker para o backend
  - `Render Postgres` gerido
  - `DATABASE_URL` ligado ao Postgres via Blueprint
  - `healthCheckPath` em `/api/v1/health`
  - `EXECUTION_MODE=PAPER`
  - `ENABLE_LIVE_TRADING=false`
  - `EMAIL_DELIVERY_MODE=log` para demos no plano gratuito
- `Dockerfile` na raiz como fallback para o Render quando o serviço Docker é criado fora do fluxo de Blueprint
- `infra/backend.Dockerfile` atualizado para respeitar a variável `PORT`
- [backend/.env.render.example](C:/Users/Rodrigo🐐/OneDrive/Desktop/AlphaView-Dashboard/backend/.env.render.example) com os overrides mínimos

## Como criar o backend no Render

1. Faça push do repositório para GitHub.
2. No Render, escolha `New > Blueprint`.
3. Ligue o repositório e selecione o ficheiro `render.yaml` da raiz.
4. O Blueprint já fica pré-configurado com o frontend:

```env
FRONTEND_BASE_URL=https://alphaview.netlify.app
BACKEND_CORS_ORIGINS=https://alphaview.netlify.app
```

Se o domínio do frontend mudar no futuro, ajuste esses dois valores no Render.

5. Confirme a criação do serviço `alphaview-backend` e da base de dados `alphaview-db`.

Se você já tiver criado um `Web Service` normal em vez de `Blueprint`, o repositório agora também funciona nesse modo porque o Render encontrará o `Dockerfile` na raiz por defeito.

## O que o Render vai criar

- um web service público para o FastAPI
- uma base de dados Postgres gratuita

O serviço usa `Docker`, faz health check em:

```text
/api/v1/health
```

e liga ao Postgres com a `connectionString` privada do próprio Render.

## Variáveis importantes

Estas variáveis já ficam definidas pelo `render.yaml`:

```env
APP_ENV=production
EXECUTION_MODE=PAPER
ENABLE_LIVE_TRADING=false
AUTH_COOKIE_SECURE=true
ALLOW_PUBLIC_REGISTRATION=true
EMAIL_DELIVERY_MODE=log
PORT=10000
```

Estas já ficam definidas pelo `render.yaml`:

```env
FRONTEND_BASE_URL=https://alphaview.netlify.app
BACKEND_CORS_ORIGINS=https://alphaview.netlify.app
```

Variáveis opcionais que você pode acrescentar depois, se precisar:

```env
EMAIL_SMTP_HOST=
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USERNAME=
EMAIL_SMTP_PASSWORD=
EMAIL_FROM_EMAIL=
POLYGON_API_KEY=
EODHD_API_TOKEN=
STRIPE_PUBLISHABLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
```

## Como ligar com a Netlify

Depois do primeiro deploy do backend, copie a URL pública do Render, por exemplo:

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

Se estiver a usar `EMAIL_DELIVERY_MODE=log`, os códigos de verificação aparecem nos logs do Render em vez de serem enviados por SMTP.

## Limitações conhecidas

- O plano gratuito do Render faz o web service entrar em idle após inatividade.
- O Postgres gratuito expira `30 dias` após a criação.
- O plano gratuito do Render bloqueia SMTP nas portas `25`, `465` e `587`; por isso o Blueprint fica em `EMAIL_DELIVERY_MODE=log` por defeito.
- O arranque da aplicação ainda cria o schema de forma bootstrap-style; não há Alembic neste milestone.

## Próximo passo recomendado

Adicionar um worker/cron no Render para backfill, feature materialization e retraining, em vez de deixar esses processos apenas para execução manual.

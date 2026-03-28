<div align="center">

# ðŸ“Š AlphaView Dashboard

### Professional Equities Research & Simulation Platform

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

<img src="https://img.shields.io/badge/Status-Production_Ready-76F9B5?style=for-the-badge" alt="Status" />
<img src="https://img.shields.io/badge/License-Proprietary-FFB069?style=for-the-badge" alt="License" />

---

### ðŸŽ¯ O que Ã© o AlphaView?

**AlphaView Dashboard** Ã© uma plataforma institucional de pesquisa e simulaÃ§Ã£o de aÃ§Ãµes do mercado americano, construÃ­da com arquitetura de produÃ§Ã£o. Combina ingestÃ£o de dados histÃ³ricos de mercado, engenharia de features time-series-safe, modelos supervisionados de machine learning, geraÃ§Ã£o de sinais de trading, backtesting robusto e simulaÃ§Ã£o de execuÃ§Ã£o em tempo real.

**Ideal para:** Mesas de trading internas, fundos quantitativos, plataformas SaaS financeiras, ou como ativo tÃ©cnico modular para aquisiÃ§Ã£o.

</div>

---

## âœ¨ Principais Recursos

### ðŸ“ˆ Dados & Engenharia
- âœ… Backfill histÃ³rico com adaptador Polygon + fallback sintÃ©tico
- âœ… PersistÃªncia OHLCV normalizada em PostgreSQL via SQLAlchemy
- âœ… Features materializadas: returns, SMA, EMA, RSI, MACD, ATR, volatilidade, volume e flags de sessÃ£o

### ðŸ¤– Machine Learning
- âœ… Modelos baseline supervisionados (Logistic Regression, Gradient Boosting)
- âœ… PersistÃªncia de runs e prediÃ§Ãµes
- âœ… GeraÃ§Ã£o de sinais BUY / SELL / HOLD

### ðŸŽ® SimulaÃ§Ã£o & Backtesting
- âœ… Backtester com custos, slippage, cooldown, max daily loss e mÃ©tricas detalhadas
- âœ… Simulador de execuÃ§Ã£o local com tracking de ordens, execuÃ§Ãµes e posiÃ§Ãµes
- âœ… Demo seed flow completo para ambiente de demonstraÃ§Ã£o
- âœ… Infraestrutura de email transacional HTML com branding AlphaView

### ðŸ–¥ï¸ Dashboard Profissional
- âœ… Interface React multi-pÃ¡gina: Overview, Signals, Positions, Trades, Backtests, Models, Logs, Settings
- âœ… Browser de mercados/sÃ­mbolos no Overview para carregar o grÃ¡fico de candles por exchange
- âœ… Dashboard orientado por padrÃ£o para Europa, com universe/quotes via EODHD e candles europeus via EODHD daily ou IBKR intraday no Overview
- âœ… PÃ¡ginas operacionais com hero KPI, cartÃµes de prioridade e tabelas com contexto para sinais, exposiÃ§Ã£o, execuÃ§Ã£o, modelos, backtests e logs
- âœ… SuperfÃ­cies de Account, Billing e Settings com estados visuais, resumos executivos e fluxos mais claros
- âœ… Redesign completo do shell com navegaÃ§Ã£o em secÃ§Ãµes, topbar operacional e autenticaÃ§Ã£o em layout command-center
- âœ… Design moderno com gradientes, glassmorphism e animaÃ§Ãµes suaves
- âœ… VisualizaÃ§Ãµes em tempo real e mÃ©tricas de performance

---

## ðŸ—ï¸ Posicionamento Comercial

### âœ… Este projeto Ã‰:
- ðŸ¢ Infraestrutura de pesquisa quantitativa para equities
- ðŸ“Š Plataforma de simulaÃ§Ã£o com dados reais de mercado
- ðŸ”§ Ativo tÃ©cnico modular para desks internos, evoluÃ§Ã£o SaaS ou handover

### âŒ Este projeto NÃƒO Ã©:
- ðŸ’° Sistema de lucro garantido
- ðŸ¤– AI trader sempre correto
- ðŸš€ Engine de live-trading pronto para produÃ§Ã£o sem ajustes

---

## ðŸ› ï¸ Stack TecnolÃ³gico

<table>
<tr>
<td width="50%">

### Backend
- ðŸ **Python 3.11+**
- âš¡ **FastAPI** - API moderna e assÃ­ncrona
- ðŸ’¾ **SQLAlchemy** - ORM robusto
- ðŸ“ˆ **pandas & numpy** - Processamento de dados
- ðŸ¤– **scikit-learn** - Machine Learning

</td>
<td width="50%">

### Frontend
- âš›ï¸ **React 18+**
- ðŸ”· **TypeScript** - Type safety
- âš¡ **Vite** - Build tool rÃ¡pido
- ðŸŽ¨ **CSS Moderno** - Glassmorphism design

</td>
</tr>
<tr>
<td width="50%">

### Infraestrutura
- ðŸ³ **Docker & Docker Compose**
- ðŸ“¦ **Nginx** - Serving de produÃ§Ã£o

</td>
<td width="50%">

### Database
- ðŸ˜ **PostgreSQL** - PersistÃªncia robusta

</td>
</tr>
</table>

---

## ðŸš€ Quick Start

### 1ï¸âƒ£ Configurar ambiente

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Preencha pelo menos `backend/.env` com `AUTH_SECRET_KEY` e as chaves Stripe se for testar onboarding/billing.

### 2ï¸âƒ£ Iniciar a stack completa

```powershell
docker compose up --build
```

### 3ï¸âƒ£ Acessar os serviÃ§os

| ServiÃ§o | URL | DescriÃ§Ã£o |
|---------|-----|-------------|
| ðŸ–¥ï¸ **Frontend** | `http://localhost:5173` | Dashboard principal |
| ðŸ”Œ **Backend API** | `http://localhost:18000` | API REST |
| â¤ï¸ **Health Check** | `http://localhost:18000/api/v1/health` | Status do sistema |
| ðŸŽ® **Demo Snapshot** | `http://localhost:18000/api/v1/demo/snapshot` | Dados de demonstraÃ§Ã£o |
| ðŸ”— **API Proxy** | `http://localhost:5173/api/v1/health` | Proxy frontend-backend |

---

## ðŸ” Login e Saques

- O frontend agora exige autenticaÃ§Ã£o antes de carregar o dashboard.
- O backend cria utilizadores reais em base de dados e usa cookies `HttpOnly` com sessÃµes revogÃ¡veis.
- Novas contas entram diretamente no dashboard apÃ³s o registo.
- O menu **Account** concentra onboarding Stripe Connect, sincronizaÃ§Ã£o de estado e pedidos de saque.
- `WITHDRAWALS_ENABLED=false` continua a ser o default. Ative explicitamente para testar saques.
- O saldo sacÃ¡vel Ã© um ledger dedicado; PnL simulado de PAPER trading nÃ£o vira dinheiro real automaticamente.

### VariÃ¡veis novas

```env
ALLOW_PUBLIC_REGISTRATION=true
AUTH_SECRET_KEY=change-me-in-production
IBKR_HOST=host.docker.internal
IBKR_PORT=7497
EODHD_API_TOKEN=
WITHDRAWALS_ENABLED=false
STRIPE_PUBLISHABLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_CONNECT_MODE=auto
STRIPE_WEBHOOK_SECRET=
STRIPE_CHECKOUT_SUCCESS_URL=
STRIPE_CHECKOUT_CANCEL_URL=
FRONTEND_BASE_URL=http://localhost:5173
```

### Fluxo recomendado

1. Copie `backend/.env.example` para `backend/.env` e `frontend/.env.example` para `frontend/.env`.
2. Preencha `backend/.env` com as variÃ¡veis de auth, Stripe, `EODHD_API_TOKEN` para universe/quotes europeus e `IBKR_HOST` se quiser candles intraday europeus no dashboard.
3. Suba a stack com `docker compose up --build`.
4. Crie a primeira conta no ecrÃ£ de login do frontend.
5. Entre em **Account** para ligar a conta Stripe e concluir o onboarding.
6. Entre em **Billing** para abrir o Stripe Checkout ou o Billing Portal.
7. `STRIPE_CONNECT_MODE=auto` tenta `Accounts v2` primeiro e recua para `v1/accounts` quando a plataforma Stripe ainda nÃƒÂ£o tem `Accounts v2` ativo.
8. Configure os URLs de `STRIPE_CHECKOUT_*` e o `STRIPE_WEBHOOK_SECRET` antes de expor o fluxo de billing.
9. Ative `WITHDRAWALS_ENABLED=true` apenas quando quiser testar pedidos de saque em modo de teste.

---

## ðŸŽ® Demo Flow - Ambiente Completo

Para popular o sistema com dados de demonstraÃ§Ã£o/vendas:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:18000/api/v1/demo/seed `
  -ContentType 'application/json' `
  -Body '{"symbols":["AAPL","MSFT","NVDA"],"timeframe":"1min","days":5}'
```

âœ… **ApÃ³s o seed, atualize o dashboard e veja:**
- ðŸ“Š Overview com mÃ©tricas consolidadas
- ðŸš¦ Sinais de trading (BUY/SELL/HOLD)
- ðŸ’¼ PosiÃ§Ãµes e ordens simuladas
- ðŸ“ˆ Backtests com performance histÃ³rica
- ðŸ¤– Modelos treinados e prediÃ§Ãµes
- ðŸ“ Logs de execuÃ§Ã£o

---

## ðŸ’» Desenvolvimento Local

### ðŸ Backend

```powershell
# Criar ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# Instalar dependÃªncias
pip install -r backend/requirements.txt

# Executar testes
cd backend
$env:DATABASE_URL = "sqlite+pysqlite:///:memory:"
python -m pytest
```

### âš›ï¸ Frontend

```powershell
cd frontend
npm install
npm run dev
```

> ðŸ’¡ **Nota:** Em desenvolvimento local, o Vite lÃª `frontend/.env` e faz proxy de `/api` para `http://localhost:18000` por defeito, ou para `VITE_DEV_API_PROXY` se esse valor estiver definido.
>
> O backend lÃª `backend/.env`. O projeto nÃ£o depende mais de `.env` na raiz.

---

## âš™ï¸ Workers Ãšteis

### ðŸ“‰ Backfill de dados de mercado

```powershell
cd backend
python -m app.workers.backfill_worker `
  --symbol AAPL `
  --timeframe 1min `
  --start 2026-01-05T14:30:00Z `
  --end 2026-01-10T20:00:00Z `
  --source synthetic
```

### ðŸ”§ Materializar features

```powershell
cd backend
python -m app.workers.feature_worker `
  --symbol AAPL `
  --timeframe 1min `
  --pipeline-version v1
```

### ðŸ¤– Retreinar modelos baseline

```powershell
cd backend
python -m app.workers.retrain_worker `
  --symbol AAPL `
  --timeframe 1min
```

---

## ðŸ”Œ Principais Rotas da API

| MÃ©todo | Endpoint | DescriÃ§Ã£o |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Criar conta do dashboard e abrir sessÃ£o imediatamente |
| `POST` | `/api/v1/auth/login` | Autenticar utilizador |
| `GET` | `/api/v1/auth/me` | Obter utilizador autenticado |
| `POST` | `/api/v1/market-data/backfill` | Backfill de dados histÃ³ricos |
| `GET` | `/api/v1/market-data/bars` | Consultar barras OHLCV, com `1day` via EODHD e refresh intraday europeu via IBKR quando o Gateway/TWS estiver disponÃ­vel |
| `GET` | `/api/v1/market-data/symbols` | Listar sÃ­mbolos/mercados rastreados para o grÃ¡fico |
| `GET` | `/api/v1/market-data/universe` | Pesquisar o universo europeu via EODHD, com quotes reais/delayed da EODHD e fallback local quando necessÃ¡rio |
| `POST` | `/api/v1/features/materialize` | Materializar features |
| `POST` | `/api/v1/models/train` | Treinar modelo |
| `GET` | `/api/v1/models/latest` | Obter Ãºltimo modelo |
| `POST` | `/api/v1/signals/generate` | Gerar sinais de trading |
| `POST` | `/api/v1/backtests/run` | Executar backtest |
| `GET` | `/api/v1/broker/status` | Status do broker |
| `POST` | `/api/v1/broker/orders` | Criar ordem |
| `GET` | `/api/v1/demo/snapshot` | Snapshot de demonstraÃ§Ã£o |
| `POST` | `/api/v1/demo/seed` | Popular dados de demo |
| `GET` | `/api/v1/wallet/summary` | Resumo do saldo sacÃ¡vel e estado Stripe |
| `POST` | `/api/v1/wallet/stripe/onboarding-link` | Criar/retomar onboarding Stripe Connect |
| `POST` | `/api/v1/wallet/withdrawals` | Pedir saque |
| `GET` | `/api/v1/billing/summary` | Estado local de billing e Stripe Customer |
| `POST` | `/api/v1/billing/checkout-session` | Criar sessÃ£o Stripe Checkout |
| `POST` | `/api/v1/billing/portal-session` | Criar sessÃ£o do Stripe Billing Portal |
| `POST` | `/api/v1/billing/webhook` | Receber webhooks Stripe para sincronizaÃ§Ã£o |

---

## ðŸ“ Estrutura do Projeto

```text
ðŸ“‚ AlphaView-Dashboard/
â”œâ”€â”€ ðŸ backend/          # FastAPI app, services, ORM models, tests, workers
â”œâ”€â”€ âš›ï¸ frontend/         # React dashboard com TypeScript
â”œâ”€â”€ ðŸ“š docs/             # Product spec, arquitetura, API, metodologia
â”œâ”€â”€ ðŸ¤– ml/               # CLI wrappers e utilitÃ¡rios de pesquisa
â”œâ”€â”€ ðŸ“„ reports/          # Artefatos de modelos e relatÃ³rios de backtest
â””â”€â”€ ðŸ“ examples/         # SÃ­mbolos de exemplo, demo seed e configs
```

---

## ðŸ“š DocumentaÃ§Ã£o Completa

| Documento | DescriÃ§Ã£o |
|-----------|-------------|
| ðŸ“ [Product Spec](docs/product_spec.md) | EspecificaÃ§Ã£o completa do produto |
| ðŸ—ï¸ [Architecture](docs/architecture.md) | Arquitetura tÃ©cnica detalhada |
| ðŸ”Œ [API Contracts](docs/api_contracts.md) | Contratos e schemas da API |
| ðŸ“ˆ [Backtest Methodology](docs/backtest_methodology.md) | Metodologia de backtesting |
| ðŸ¤ [Buyer Handover](docs/buyer_handover.md) | Guia de handover para compradores |
| ðŸŽ¯ [Sales Demo Script](docs/sales_demo_script.md) | Script de demonstraÃ§Ã£o comercial |
| ðŸ’° [Valuation Notes](docs/valuation_notes.md) | Notas de valuaÃ§Ã£o |

---

## âš ï¸ LimitaÃ§Ãµes Conhecidas

- ðŸ”Œ Suporte histÃ³rico Polygon implementado, mas websocket live ainda nÃ£o estÃ¡ production-hardened
- ðŸ’¼ IntegraÃ§Ã£o IBKR representada por camada de simulaÃ§Ã£o segura, nÃ£o Ã© stack TWS/Gateway completo
- ðŸ’¾ MigraÃ§Ãµes de schema ainda sÃ£o bootstrap-style; Alembic serÃ¡ adicionado futuramente
- ðŸ“‰ Backtesting Ã© intencionalmente simples e research-oriented, nÃ£o Ã© simulaÃ§Ã£o de portfÃ³lio execution-grade
- ðŸ¤– Reinforcement learning permanece fora do escopo do baseline vendÃ¡vel
- ðŸ’³ Billing Stripe jÃ¡ estÃ¡ ligado ao dashboard, mas ainda depende de `price_id` manual e nÃ£o tem catÃ¡logo interno de planos
- âœ‰ï¸ A entrega de emails transacionais depende do provider configurado e de credenciais vÃ¡lidas
- ðŸŒ O universo e as cotaÃ§Ãµes europeias agora dependem de `EODHD_API_TOKEN`; candles intraday europeus continuam a depender de `IBKR_HOST` e do IBKR Gateway/TWS
- ðŸ“‰ O token EODHD atual nÃ£o tem entitlement intraday; `1min/5min/15min` na Europa continuam a degradar para IBKR ou preview sintÃ©tico

---

## ðŸ›£ï¸ Roadmap

- [ ] ðŸ”„ Substituir mock broker adapter por integraÃ§Ã£o IBKR paper gateway hardened
- [ ] ðŸ’¾ Adicionar migraÃ§Ãµes Alembic e gestÃ£o de ciclo de vida de persistÃªncia
- [ ] ðŸ“… Adicionar visibilidade de retreinamento agendado diretamente no dashboard
- [ ] ðŸ“Š Expandir backtesting multi-sÃ­mbolo de portfÃ³lio e polÃ­ticas de promoÃ§Ã£o de modelos

---

<div align="center">

### ðŸš€ ConstruÃ­do com excelÃªncia para trading quantitativo profissional

**AlphaView Dashboard** - Where Data Meets Alpha

ðŸ“Š ðŸ¤– ðŸ“ˆ

</div>


<div align="center">

# 📊 AlphaView Dashboard

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

### 🎯 O que é o AlphaView?

**AlphaView Dashboard** é uma plataforma institucional de pesquisa e simulação de ações do mercado americano, construída com arquitetura de produção. Combina ingestão de dados históricos de mercado, engenharia de features time-series-safe, modelos supervisionados de machine learning, geração de sinais de trading, backtesting robusto e simulação de execução em tempo real.

**Ideal para:** Mesas de trading internas, fundos quantitativos, plataformas SaaS financeiras, ou como ativo técnico modular para aquisição.

</div>

---

## ✨ Principais Recursos

### 📈 Dados & Engenharia
- ✅ Backfill histórico com adaptador Polygon + fallback sintético
- ✅ Persistência OHLCV normalizada em PostgreSQL via SQLAlchemy
- ✅ Features materializadas: returns, SMA, EMA, RSI, MACD, ATR, volatilidade, volume e flags de sessão

### 🤖 Machine Learning
- ✅ Modelos baseline supervisionados (Logistic Regression, Gradient Boosting)
- ✅ Persistência de runs e predições
- ✅ Geração de sinais BUY / SELL / HOLD

### 🎮 Simulação & Backtesting
- ✅ Backtester com custos, slippage, cooldown, max daily loss e métricas detalhadas
- ✅ Simulador de execução local com tracking de ordens, execuções e posições
- ✅ Demo seed flow completo para ambiente de demonstração
- ✅ Infraestrutura de email transacional HTML com branding AlphaView

### 🖥️ Dashboard Profissional
- ✅ Interface React multi-página: Overview, Signals, Positions, Trades, Backtests, Models, Logs, Settings
- ✅ Browser de mercados/símbolos no Overview para carregar o gráfico de candles por exchange
- ✅ Dashboard orientado por padrão para Europa, com universe/quotes via EODHD e candles europeus via EODHD daily ou IBKR intraday no Overview
- ✅ Páginas operacionais com hero KPI, cartões de prioridade e tabelas com contexto para sinais, exposição, execução, modelos, backtests e logs
- ✅ Superfícies de Account, Billing e Settings com estados visuais, resumos executivos e fluxos mais claros
- ✅ Redesign completo do shell com navegação em secções, topbar operacional e autenticação em layout command-center
- ✅ Design moderno com gradientes, glassmorphism e animações suaves
- ✅ Visualizações em tempo real e métricas de performance

---

## 🏗️ Posicionamento Comercial

### ✅ Este projeto É:
- 🏢 Infraestrutura de pesquisa quantitativa para equities
- 📊 Plataforma de simulação com dados reais de mercado
- 🔧 Ativo técnico modular para desks internos, evolução SaaS ou handover

### ❌ Este projeto NÃO é:
- 💰 Sistema de lucro garantido
- 🤖 AI trader sempre correto
- 🚀 Engine de live-trading pronto para produção sem ajustes

---

## 🛠️ Stack Tecnológico

<table>
<tr>
<td width="50%">

### Backend
- 🐍 **Python 3.11+**
- ⚡ **FastAPI** - API moderna e assíncrona
- 💾 **SQLAlchemy** - ORM robusto
- 📈 **pandas & numpy** - Processamento de dados
- 🤖 **scikit-learn** - Machine Learning

</td>
<td width="50%">

### Frontend
- ⚛️ **React 18+**
- 🔷 **TypeScript** - Type safety
- ⚡ **Vite** - Build tool rápido
- 🎨 **CSS Moderno** - Glassmorphism design

</td>
</tr>
<tr>
<td width="50%">

### Infraestrutura
- 🐳 **Docker & Docker Compose**
- 📦 **Nginx** - Serving de produção

</td>
<td width="50%">

### Database
- 🐘 **PostgreSQL** - Persistência robusta

</td>
</tr>
</table>

---

## 🚀 Quick Start

### 1️⃣ Configurar ambiente

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Preencha pelo menos `backend/.env` com `AUTH_SECRET_KEY`, `EMAIL_SMTP_*`, `EMAIL_FROM_EMAIL` e as chaves Stripe se for testar onboarding/billing.

### 2️⃣ Iniciar a stack completa

```powershell
docker compose up --build
```

### 3️⃣ Acessar os serviços

| Serviço | URL | Descrição |
|---------|-----|-------------|
| 🖥️ **Frontend** | `http://localhost:5173` | Dashboard principal |
| 🔌 **Backend API** | `http://localhost:18000` | API REST |
| ❤️ **Health Check** | `http://localhost:18000/api/v1/health` | Status do sistema |
| 🎮 **Demo Snapshot** | `http://localhost:18000/api/v1/demo/snapshot` | Dados de demonstração |
| 🔗 **API Proxy** | `http://localhost:5173/api/v1/health` | Proxy frontend-backend |

---

## 🔐 Login e Saques

- O frontend agora exige autenticação antes de carregar o dashboard.
- O backend cria utilizadores reais em base de dados e usa cookies `HttpOnly` com sessões revogáveis.
- Novas contas entram diretamente no dashboard após o registo; a verificação de email está desativada neste momento.
- O menu **Account** concentra onboarding Stripe Connect, sincronização de estado e pedidos de saque.
- `WITHDRAWALS_ENABLED=false` continua a ser o default. Ative explicitamente para testar saques.
- O saldo sacável é um ledger dedicado; PnL simulado de PAPER trading não vira dinheiro real automaticamente.

### Variáveis novas

```env
ALLOW_PUBLIC_REGISTRATION=true
AUTH_SECRET_KEY=change-me-in-production
AUTH_VERIFICATION_CODE_TTL_MINUTES=10
AUTH_VERIFICATION_RESEND_COOLDOWN_SECONDS=60
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USERNAME=
EMAIL_SMTP_PASSWORD=
EMAIL_FROM_EMAIL=
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
2. Preencha `backend/.env` com as variáveis de auth, SMTP Gmail-compatible, Stripe, `EODHD_API_TOKEN` para universe/quotes europeus e `IBKR_HOST` se quiser candles intraday europeus no dashboard.
3. Suba a stack com `docker compose up --build`.
4. Crie a primeira conta no ecrã de login do frontend.
5. Entre em **Account** para ligar a conta Stripe e concluir o onboarding.
6. Entre em **Billing** para abrir o Stripe Checkout ou o Billing Portal.
7. `STRIPE_CONNECT_MODE=auto` tenta `Accounts v2` primeiro e recua para `v1/accounts` quando a plataforma Stripe ainda nÃ£o tem `Accounts v2` ativo.
8. Configure os URLs de `STRIPE_CHECKOUT_*` e o `STRIPE_WEBHOOK_SECRET` antes de expor o fluxo de billing.
9. Ative `WITHDRAWALS_ENABLED=true` apenas quando quiser testar pedidos de saque em modo de teste.

---

## 🎮 Demo Flow - Ambiente Completo

Para popular o sistema com dados de demonstração/vendas:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:18000/api/v1/demo/seed `
  -ContentType 'application/json' `
  -Body '{"symbols":["AAPL","MSFT","NVDA"],"timeframe":"1min","days":5}'
```

✅ **Após o seed, atualize o dashboard e veja:**
- 📊 Overview com métricas consolidadas
- 🚦 Sinais de trading (BUY/SELL/HOLD)
- 💼 Posições e ordens simuladas
- 📈 Backtests com performance histórica
- 🤖 Modelos treinados e predições
- 📝 Logs de execução

---

## 💻 Desenvolvimento Local

### 🐍 Backend

```powershell
# Criar ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# Instalar dependências
pip install -r backend/requirements.txt

# Executar testes
cd backend
$env:DATABASE_URL = "sqlite+pysqlite:///:memory:"
python -m pytest
```

### ⚛️ Frontend

```powershell
cd frontend
npm install
npm run dev
```

> 💡 **Nota:** Em desenvolvimento local, o Vite lê `frontend/.env` e faz proxy de `/api` para `http://localhost:18000` por defeito, ou para `VITE_DEV_API_PROXY` se esse valor estiver definido.
>
> O backend lê `backend/.env`. O projeto não depende mais de `.env` na raiz.

---

## ⚙️ Workers Úteis

### 📉 Backfill de dados de mercado

```powershell
cd backend
python -m app.workers.backfill_worker `
  --symbol AAPL `
  --timeframe 1min `
  --start 2026-01-05T14:30:00Z `
  --end 2026-01-10T20:00:00Z `
  --source synthetic
```

### 🔧 Materializar features

```powershell
cd backend
python -m app.workers.feature_worker `
  --symbol AAPL `
  --timeframe 1min `
  --pipeline-version v1
```

### 🤖 Retreinar modelos baseline

```powershell
cd backend
python -m app.workers.retrain_worker `
  --symbol AAPL `
  --timeframe 1min
```

---

## 🔌 Principais Rotas da API

| Método | Endpoint | Descrição |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Criar conta do dashboard e abrir sessão imediatamente |
| `POST` | `/api/v1/auth/login` | Autenticar utilizador |
| `GET` | `/api/v1/auth/me` | Obter utilizador autenticado |
| `POST` | `/api/v1/market-data/backfill` | Backfill de dados históricos |
| `GET` | `/api/v1/market-data/bars` | Consultar barras OHLCV, com `1day` via EODHD e refresh intraday europeu via IBKR quando o Gateway/TWS estiver disponível |
| `GET` | `/api/v1/market-data/symbols` | Listar símbolos/mercados rastreados para o gráfico |
| `GET` | `/api/v1/market-data/universe` | Pesquisar o universo europeu via EODHD, com quotes reais/delayed da EODHD e fallback local quando necessário |
| `POST` | `/api/v1/features/materialize` | Materializar features |
| `POST` | `/api/v1/models/train` | Treinar modelo |
| `GET` | `/api/v1/models/latest` | Obter último modelo |
| `POST` | `/api/v1/signals/generate` | Gerar sinais de trading |
| `POST` | `/api/v1/backtests/run` | Executar backtest |
| `GET` | `/api/v1/broker/status` | Status do broker |
| `POST` | `/api/v1/broker/orders` | Criar ordem |
| `GET` | `/api/v1/demo/snapshot` | Snapshot de demonstração |
| `POST` | `/api/v1/demo/seed` | Popular dados de demo |
| `GET` | `/api/v1/wallet/summary` | Resumo do saldo sacável e estado Stripe |
| `POST` | `/api/v1/wallet/stripe/onboarding-link` | Criar/retomar onboarding Stripe Connect |
| `POST` | `/api/v1/wallet/withdrawals` | Pedir saque |
| `GET` | `/api/v1/billing/summary` | Estado local de billing e Stripe Customer |
| `POST` | `/api/v1/billing/checkout-session` | Criar sessão Stripe Checkout |
| `POST` | `/api/v1/billing/portal-session` | Criar sessão do Stripe Billing Portal |
| `POST` | `/api/v1/billing/webhook` | Receber webhooks Stripe para sincronização |

---

## 📁 Estrutura do Projeto

```text
📂 AlphaView-Dashboard/
├── 🐍 backend/          # FastAPI app, services, ORM models, tests, workers
├── ⚛️ frontend/         # React dashboard com TypeScript
├── 📚 docs/             # Product spec, arquitetura, API, metodologia
├── 🤖 ml/               # CLI wrappers e utilitários de pesquisa
├── 📄 reports/          # Artefatos de modelos e relatórios de backtest
└── 📝 examples/         # Símbolos de exemplo, demo seed e configs
```

---

## 📚 Documentação Completa

| Documento | Descrição |
|-----------|-------------|
| 📝 [Product Spec](docs/product_spec.md) | Especificação completa do produto |
| 🏗️ [Architecture](docs/architecture.md) | Arquitetura técnica detalhada |
| 🔌 [API Contracts](docs/api_contracts.md) | Contratos e schemas da API |
| 📈 [Backtest Methodology](docs/backtest_methodology.md) | Metodologia de backtesting |
| 🤝 [Buyer Handover](docs/buyer_handover.md) | Guia de handover para compradores |
| 🎯 [Sales Demo Script](docs/sales_demo_script.md) | Script de demonstração comercial |
| 💰 [Valuation Notes](docs/valuation_notes.md) | Notas de valuação |

---

## ⚠️ Limitações Conhecidas

- 🔌 Suporte histórico Polygon implementado, mas websocket live ainda não está production-hardened
- 💼 Integração IBKR representada por camada de simulação segura, não é stack TWS/Gateway completo
- 💾 Migrações de schema ainda são bootstrap-style; Alembic será adicionado futuramente
- 📉 Backtesting é intencionalmente simples e research-oriented, não é simulação de portfólio execution-grade
- 🤖 Reinforcement learning permanece fora do escopo do baseline vendável
- 💳 Billing Stripe já está ligado ao dashboard, mas ainda depende de `price_id` manual e não tem catálogo interno de planos
- ✉️ A entrega de emails transacionais depende do provider configurado e de credenciais válidas
- 🌍 O universo e as cotações europeias agora dependem de `EODHD_API_TOKEN`; candles intraday europeus continuam a depender de `IBKR_HOST` e do IBKR Gateway/TWS
- 📉 O token EODHD atual não tem entitlement intraday; `1min/5min/15min` na Europa continuam a degradar para IBKR ou preview sintético

---

## 🛣️ Roadmap

- [ ] 🔄 Substituir mock broker adapter por integração IBKR paper gateway hardened
- [ ] 💾 Adicionar migrações Alembic e gestão de ciclo de vida de persistência
- [ ] 📅 Adicionar visibilidade de retreinamento agendado diretamente no dashboard
- [ ] 📊 Expandir backtesting multi-símbolo de portfólio e políticas de promoção de modelos

---

<div align="center">

### 🚀 Construído com excelência para trading quantitativo profissional

**AlphaView Dashboard** - Where Data Meets Alpha

📊 🤖 📈

</div>

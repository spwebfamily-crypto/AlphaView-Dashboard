# Buyer Handover

## What the buyer is receiving

AlphaView Dashboard is a modular equities research and simulation platform with:

- historical market data ingestion
- persisted feature engineering
- baseline model training
- signal generation
- backtesting
- simulated order execution over real market data
- structured operational logs
- frontend dashboard with demo mode

## How to run

1. Copy `backend/.env.example` to `backend/.env`.
2. Copy `frontend/.env.example` to `frontend/.env`.
3. Start the stack with `docker compose up --build`.
4. Open the frontend on `http://localhost:5173`.
5. The frontend container proxies `/api` to the backend.
6. If the dashboard is empty, run `POST /api/v1/demo/seed`.

## Important runtime defaults

- execution mode defaults to `PAPER`
- live trading is disabled by default
- demo flow works without external market-data APIs

## Main modules

- `backend/app/services/market_data_service.py`: data ingestion and synthetic fallback
- `backend/app/services/feature_service.py`: feature materialization
- `backend/app/services/model_service.py`: supervised baselines and inference
- `backend/app/services/backtest_service.py`: research backtests and report output
- `backend/app/services/broker_service.py`: local execution simulator
- `frontend/src/App.tsx`: dashboard orchestration

## Risks and gaps

- real IBKR paper routing still needs a hardened adapter
- live websocket ingestion is not yet production-hardened
- database migrations are not fully formalized with Alembic
- backtester is simplified and should not be presented as execution-grade

## Suggested next owner priorities

1. Replace mock broker adapter with true IBKR paper execution.
2. Add Alembic migrations and stronger artifact lifecycle handling.
3. Add scheduled retraining visibility and model promotion controls.
4. Harden multi-symbol portfolio analytics.

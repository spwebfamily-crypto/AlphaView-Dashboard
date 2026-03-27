# Project Instructions

You are implementing a production-style research and paper-trading platform for US equities.

## Product goal
Build a modular platform for:
- historical and real-time market data ingestion
- feature engineering
- supervised ML forecasting
- strategy and risk controls
- backtesting
- paper trading
- monitoring dashboard
- buyer/demo presentation assets

## Constraints
- Default execution mode must be PAPER only.
- LIVE trading must remain disabled by default.
- Never claim guaranteed returns or certainty.
- The product is for equities, not crypto.
- Focus on US stocks first.
- Respect market sessions and time-series correctness.
- Prefer a clean, maintainable architecture over premature optimization.

## APIs
- Polygon for historical and streaming stock market data
- Interactive Brokers for paper trading execution

## Engineering rules
- Use Python for backend and ML
- Use FastAPI for backend API
- Use PostgreSQL for persistence
- Use React + TypeScript for dashboard
- Add Docker support
- Add `.env.example`
- Add structured logging
- Add retry/reconnect logic for external APIs
- Keep services loosely coupled
- Add tests for critical paths

## ML rules
- Implement supervised baseline before RL
- Use time-series split only
- Prevent leakage and lookahead bias
- Save model artifacts and experiment metadata
- Include metrics: Sharpe, max drawdown, win rate, expectancy, profit factor

## Delivery rules
For every milestone:
1. implement code
2. add tests
3. update docs
4. explain how to run
5. list known limitations
6. propose the next milestone

## Safety and commercial positioning
- Present the system as a research and paper-trading platform
- Do not present backtests as proof of future performance
- Include demo mode for commercial presentation


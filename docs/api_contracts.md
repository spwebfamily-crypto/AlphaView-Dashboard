# API Contracts

## Health

- `GET /api/v1/health`
- Returns service status, environment, execution mode, live-trading flag, and database status.

## Market data

- `POST /api/v1/market-data/backfill`
- Inputs: `symbol`, `timeframe`, `start`, `end`, `source`
- Outputs: inserted row count and selected source (`polygon`, `finnhub`, or `synthetic`)

- `GET /api/v1/market-data/bars`
- Query: `symbol`, `timeframe`, optional `start`, `end`, `limit`
- Returns normalized OHLCV rows

- `GET /api/v1/market-data/market-status`
- Query: `exchange`
- Returns the live open/closed session state for the requested exchange through the Finnhub adapter

- `GET /api/v1/market-data/stream/preview`
- Query: `symbol`, `timeframe`, `points`
- Returns a synthetic preview stream for dashboard/demo use

## Features

- `POST /api/v1/features/materialize`
- Inputs: `symbol`, `timeframe`, `pipeline_version`
- Returns number of persisted feature rows

- `GET /api/v1/features`
- Returns persisted feature rows for a symbol/timeframe/version

## Models

- `POST /api/v1/models/train`
- Inputs: `symbol`, `timeframe`, `pipeline_version`, optional thresholds
- Trains logistic regression and gradient boosting baselines
- Persists model runs and champion predictions

- `GET /api/v1/models/runs`
- Returns model run history

- `GET /api/v1/models/latest`
- Returns latest inference payload for a symbol/timeframe

## Signals

- `POST /api/v1/signals/generate`
- Converts predictions to `BUY`, `SELL`, or `HOLD`

- `GET /api/v1/signals`
- Lists recent signals

## Backtests

- `POST /api/v1/backtests/run`
- Inputs: `symbol`, `timeframe`, optional risk and execution parameters
- Returns metrics, equity curve, and trade list

- `GET /api/v1/backtests`
- Lists recent backtest runs

- `GET /api/v1/backtests/{id}`
- Returns a full stored backtest run

## Broker

- `GET /api/v1/broker/status`
- Returns simulation-adapter mode and connectivity probe result

- `POST /api/v1/broker/orders`
- Places a simulated order through the local execution engine

- `POST /api/v1/broker/orders/{id}/cancel`
- Cancels a submitted simulated order

- `GET /api/v1/broker/orders`
- Lists orders

- `GET /api/v1/broker/executions`
- Lists executions

- `GET /api/v1/broker/positions`
- Lists positions

## Demo

- `POST /api/v1/demo/seed`
- Seeds synthetic bars, features, models, signals, backtests, and simulated orders

- `GET /api/v1/demo/snapshot`
- Returns a buyer/demo-friendly dashboard snapshot

## Runtime

- `GET /api/v1/settings/runtime`
- Returns environment defaults used by the platform

- `GET /api/v1/logs`
- Returns recent structured system logs

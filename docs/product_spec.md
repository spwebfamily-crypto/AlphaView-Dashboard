# Product Spec

## Positioning

AlphaView Dashboard is a research, simulation, and paper-trading platform for US equities. It is designed as a modular technical asset for quantitative workflows, operator monitoring, demo presentation, and buyer handover.

## Current scope

- historical OHLCV ingestion with Polygon-compatible adapter and synthetic fallback
- persisted feature engineering with time-series-safe calculations
- supervised baseline model training and inference
- signal generation and risk-aware backtesting
- paper broker mock adapter with orders, executions, and positions
- seeded demo mode for sales and presentation
- React dashboard for monitoring and presentation

## Safety rules

- `PAPER` is the default execution mode
- `LIVE` remains disabled unless explicitly enabled later
- the platform must not imply guaranteed profitability
- backtests are research artifacts, not proof of future results

## Users

- founder/operator validating research workflows
- technical buyer evaluating the platform as a sellable asset
- quant/dev team extending data, models, execution, and dashboard layers

## Non-goals for the current sellable baseline

- default live trading
- production reinforcement learning execution
- marketing claims around guaranteed returns


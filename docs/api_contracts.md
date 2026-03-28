# API Contracts

## Health

- `GET /api/v1/health`
- Returns service status, environment, execution mode, live-trading flag, and database status.

## Auth

- `POST /api/v1/auth/register`
- Inputs: `email`, `password`, optional `full_name`
- Creates a real user record in the database, validates password strength, issues a confirmation code, and sends a branded HTML email over the configured SMTP/Gmail-compatible mailbox

- `POST /api/v1/auth/login`
- Inputs: `email`, `password`
- Authenticates the dashboard user only after the email address has been confirmed

- `POST /api/v1/auth/refresh`
- Rotates the refresh session and renews the access cookie without exposing tokens to the frontend runtime

- `POST /api/v1/auth/logout`
- Revokes the stored session and clears auth cookies

- `POST /api/v1/auth/verify-email`
- Inputs: `email`, `code`
- Confirms the email verification code, marks the user as verified, creates a revocable session, and sets `HttpOnly` cookies

- `POST /api/v1/auth/resend-verification`
- Inputs: `email`
- Reissues a fresh confirmation code for an existing unverified account and sends it again via the branded SMTP email flow

- `GET /api/v1/auth/me`
- Returns the current authenticated user profile used by the dashboard shell

## Market data

- `POST /api/v1/market-data/backfill`
- Inputs: `symbol`, `timeframe`, `start`, `end`, `source`
- Outputs: inserted row count and selected source (`eodhd`, `ibkr`, `polygon`, `finnhub`, or `synthetic`)

- `GET /api/v1/market-data/bars`
- Query: `symbol`, `timeframe`, optional `start`, `end`, `limit`, `refresh`
- Returns normalized OHLCV rows
- In the Europe-oriented dashboard flow, `timeframe=1day` can sync daily bars from EODHD
- For `1min/5min/15min`, `refresh=true` still pulls recent candles from IBKR when the Gateway/TWS is reachable; otherwise the route falls back to stored bars or preview

- `GET /api/v1/market-data/symbols`
- Query: optional `exchange`, `query`, `active_only`, `limit`
- Returns the tracked equity universe used to browse markets and load the candlestick chart

- `GET /api/v1/market-data/universe`
- Query: optional `locale`, `query`, `exchange`, `active_only`, `limit`, `cursor`, `security_type`, `currency`, `include_quotes`
- Returns the Europe-oriented exchange universe through EODHD search and exchange-symbol-list endpoints, enriched with EODHD real-time/delayed quotes when available
- The route no longer depends on Polygon for the dashboard market browser; Europe universe/quotes require `EODHD_API_TOKEN`, while intraday candles still require `IBKR_HOST` plus a running IBKR Gateway/TWS session

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

## Wallet / Stripe

- `GET /api/v1/wallet/summary`
- Returns withdrawable balance, configured currency, withdrawal-engine flag, and Stripe Connect status

- `GET /api/v1/wallet/withdrawals`
- Lists persisted withdrawal requests for the authenticated user

- `POST /api/v1/wallet/stripe/onboarding-link`
- Creates or resumes a Stripe Connect recipient account and returns a hosted onboarding URL
- Supports `Accounts v2` and can fall back to legacy `v1/accounts` onboarding when the platform does not have `Accounts v2` enabled

- `POST /api/v1/wallet/stripe/refresh`
- Pulls the latest Stripe Connect account status into the local database

- `POST /api/v1/wallet/stripe/dashboard-link`
- Returns a Stripe Express dashboard login link for the connected account

- `POST /api/v1/wallet/withdrawals`
- Inputs: `amount_cents`
- Validates withdrawable cash, checks Stripe onboarding and platform balance, then creates a transfer and payout attempt in test mode when enabled

## Billing / Stripe Checkout

- `GET /api/v1/billing/summary`
- Returns the authenticated user's local Stripe customer/subscription state used by the billing UI

- `POST /api/v1/billing/checkout-session`
- Inputs: `price_id`, optional `mode` (`subscription` or `payment`), optional `quantity`, optional `plan_code`, optional success/cancel URLs
- Creates a hosted Stripe Checkout Session for the authenticated dashboard user and links metadata back to the local user id

- `POST /api/v1/billing/portal-session`
- Creates a Stripe Billing Portal session for the authenticated user's existing Stripe customer

- `POST /api/v1/billing/webhook`
- Public Stripe webhook receiver that verifies the `Stripe-Signature` header, then syncs checkout completion and subscription lifecycle state into PostgreSQL

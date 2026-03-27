# Valuation Notes

## What creates value here

- end-to-end workflow coverage from data to dashboard
- modular architecture with clear extension points
- demo mode that works without paid APIs
- persisted artifacts for model runs and backtests
- paper broker layer and operational logging
- buyer-facing documentation that lowers handover friction

## What still suppresses valuation

- no hardened IBKR production paper adapter yet
- no formal migration workflow
- backtester is simplified
- live market streaming is not yet fully operationalized

## How to improve perceived value fast

1. Replace the mock broker layer with real IBKR paper routing.
2. Add screenshots and a short demo video of the seeded dashboard.
3. Add Alembic migrations and one-command DB initialization.
4. Add multi-symbol and portfolio-level analytics.
5. Add scheduled retraining status directly to the UI.

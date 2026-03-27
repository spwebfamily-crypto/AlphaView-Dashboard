# Backtest Methodology

## Scope

The current backtester is a research-oriented engine intended to validate whether model outputs can be converted into paper-trading signals under friction. It is not a claim of future performance and is not a substitute for execution-grade simulation.

## Sequence

1. Generate time-series-safe features from stored bars.
2. Train baseline supervised models with temporal splits only.
3. Persist champion predictions on the out-of-sample test window.
4. Convert probabilities into `BUY`, `SELL`, or `HOLD`.
5. Execute simulated trades on the next bar using configurable slippage and transaction costs.
6. Apply risk gating for cooldown, max position size, max exposure per symbol, and max daily loss.

## Fill model

- Entry occurs on the next bar open after the prediction timestamp.
- Exit occurs on the same next bar close in the current simplified engine.
- Slippage is applied adversely on both entry and exit.
- Transaction costs are deducted in basis points on the round trip.

## Metrics

- total return
- Sharpe ratio
- max drawdown
- win rate
- expectancy
- profit factor
- average trade return
- trade count

## Bias controls

- temporal split only
- no shuffled train/test split
- labels based on future close relative to current close
- features use only past and current bar information

## Known simplifications

- one-bar holding logic
- single-symbol run focus
- no borrow fees, partial fills, or queue simulation
- no portfolio optimizer


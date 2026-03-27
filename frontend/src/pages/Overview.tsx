import { type FormEvent, useEffect, useState } from "react";

import { fetchMarketBars, fetchMarketPreview } from "../api/client";
import { CandlestickChart } from "../components/charts/CandlestickChart";
import { LineChart } from "../components/charts/LineChart";
import { DataTable } from "../components/DataTable";
import type { DashboardBacktest, DashboardModel, DashboardSnapshot, LatestSignal } from "../types/dashboard";
import type { MarketBar } from "../types/marketData";
import type { RuntimeSettings } from "../types/runtime";
import { formatCurrency, formatDateTime, formatPercent } from "../utils/format";

type OverviewProps = {
  snapshot: DashboardSnapshot | null;
  runtime: RuntimeSettings | null;
  loading: boolean;
  error: string | null;
};

const timeframeOptions = ["1min", "5min", "15min", "1day"];

function getSignalPriority(signalType: string) {
  if (signalType === "BUY") {
    return 3;
  }
  if (signalType === "HOLD") {
    return 2;
  }
  return 1;
}

function getSortedSignals(signals: LatestSignal[]) {
  return [...signals].sort((left, right) => {
    const priorityGap = getSignalPriority(right.signal_type) - getSignalPriority(left.signal_type);
    if (priorityGap !== 0) {
      return priorityGap;
    }
    return (right.confidence ?? 0) - (left.confidence ?? 0);
  });
}

function getLeadModel(models: DashboardModel[]) {
  return [...models].sort((left, right) => right.f1 + right.roc_auc - (left.f1 + left.roc_auc))[0] ?? null;
}

function getLeadBacktest(backtests: DashboardBacktest[]) {
  return [...backtests].sort((left, right) => right.sharpe + right.total_return - (left.sharpe + left.total_return))[0] ?? null;
}

function getNormalizedSymbol(value: string) {
  return value.replace(/[^A-Za-z.]/g, "").toUpperCase().trim();
}

function getOpportunityLabel(signal: LatestSignal | null, score: number) {
  if (!signal) {
    return "Research pending";
  }
  if (signal.signal_type === "SELL") {
    return "Avoid fresh long entry";
  }
  if (signal.signal_type === "BUY" && score >= 75) {
    return "Research for breakout buy";
  }
  if (signal.signal_type === "BUY" && score >= 60) {
    return "Watch for pullback entry";
  }
  if (signal.signal_type === "HOLD") {
    return "Monitor, no immediate trigger";
  }
  return "Wait for confirmation";
}

export function Overview({ snapshot, runtime, loading, error }: OverviewProps) {
  const rankedSignals = getSortedSignals(snapshot?.latest_signals ?? []);
  const leadModel = getLeadModel(snapshot?.models ?? []);
  const leadBacktest = getLeadBacktest(snapshot?.backtests ?? []);
  const defaultSymbol = rankedSignals[0]?.symbol ?? runtime?.default_symbols[0] ?? "AAPL";

  const [symbolInput, setSymbolInput] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [timeframe, setTimeframe] = useState("");
  const [bars, setBars] = useState<MarketBar[]>([]);
  const [barsSource, setBarsSource] = useState("historical bars");
  const [marketLoading, setMarketLoading] = useState(false);
  const [marketError, setMarketError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedSymbol) {
      setSelectedSymbol(defaultSymbol);
    }
    if (!symbolInput) {
      setSymbolInput(defaultSymbol);
    }
  }, [defaultSymbol, selectedSymbol, symbolInput]);

  useEffect(() => {
    if (!timeframe) {
      setTimeframe(runtime?.default_timeframe ?? "1min");
    }
  }, [runtime, timeframe]);

  useEffect(() => {
    if (!selectedSymbol || !timeframe) {
      return;
    }

    let active = true;

    async function loadBars() {
      setMarketLoading(true);
      setMarketError(null);

      try {
        const historicalBars = await fetchMarketBars(selectedSymbol, timeframe, 72);
        if (!active) {
          return;
        }

        if (historicalBars.length > 0) {
          setBars(historicalBars);
          setBarsSource("stored market bars");
          return;
        }

        const previewPayload = await fetchMarketPreview(selectedSymbol, timeframe, 72);
        if (!active) {
          return;
        }
        setBars(previewPayload.bars);
        setBarsSource(previewPayload.source);
      } catch (caughtError) {
        try {
          const previewPayload = await fetchMarketPreview(selectedSymbol, timeframe, 72);
          if (!active) {
            return;
          }
          setBars(previewPayload.bars);
          setBarsSource(previewPayload.source);
          setMarketError(
            caughtError instanceof Error ? `${caughtError.message}. Showing preview stream.` : "Showing preview stream.",
          );
        } catch (previewError) {
          if (!active) {
            return;
          }
          setBars([]);
          setBarsSource("unavailable");
          setMarketError(
            previewError instanceof Error ? previewError.message : "Unable to load market structure for this symbol.",
          );
        }
      } finally {
        if (active) {
          setMarketLoading(false);
        }
      }
    }

    void loadBars();

    return () => {
      active = false;
    };
  }, [selectedSymbol, timeframe]);

  function handleSymbolSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = getNormalizedSymbol(symbolInput);
    if (normalized) {
      setSelectedSymbol(normalized);
      setSymbolInput(normalized);
    }
  }

  const selectedSignal =
    rankedSignals.find((signal) => signal.symbol === selectedSymbol) ?? rankedSignals[0] ?? null;
  const latestBar = bars[bars.length - 1] ?? null;
  const firstBar = bars[0] ?? null;
  const priceMove =
    latestBar && firstBar && firstBar.open !== 0 ? ((latestBar.close - firstBar.open) / firstBar.open) * 100 : 0;
  const rangeHigh = bars.length > 0 ? Math.max(...bars.map((bar) => bar.high)) : 0;
  const rangeLow = bars.length > 0 ? Math.min(...bars.map((bar) => bar.low)) : 0;
  const averageVolume =
    bars.length > 0 ? bars.reduce((total, bar) => total + bar.volume, 0) / bars.length : 0;
  const convictionScore = Math.max(
    24,
    Math.min(
      99,
      Math.round(
        (selectedSignal?.confidence ?? 0) * 58 +
          Math.max((leadModel?.roc_auc ?? 0) - 0.5, 0) * 85 +
          Math.max(leadBacktest?.sharpe ?? 0, 0) * 9 +
          (priceMove > 0 ? 10 : 0),
      ),
    ),
  );
  const summaryFocus = (snapshot?.summary_cards ?? []).slice(0, 4);
  const researchRows = [
    {
      label: "Signal bias",
      value: selectedSignal?.signal_type ?? "N/A",
      tone: selectedSignal?.signal_type === "BUY" ? "buy" : selectedSignal?.signal_type === "SELL" ? "sell" : "hold",
      note: selectedSignal ? `${((selectedSignal.confidence ?? 0) * 100).toFixed(1)}% confidence` : "No signal mapped",
    },
    {
      label: "Price regime",
      value: `${priceMove >= 0 ? "+" : ""}${priceMove.toFixed(2)}%`,
      tone: priceMove >= 0 ? "buy" : "sell",
      note: latestBar ? `Last ${bars.length} candles on ${timeframe}` : "No bars loaded",
    },
    {
      label: "Model edge",
      value: leadModel ? `${leadModel.name} / ROC ${leadModel.roc_auc.toFixed(2)}` : "N/A",
      tone: leadModel && leadModel.roc_auc >= 0.6 ? "buy" : "hold",
      note: leadModel ? `F1 ${leadModel.f1.toFixed(2)}` : "No trained model snapshot",
    },
    {
      label: "Backtest health",
      value: leadBacktest
        ? `${formatPercent(leadBacktest.total_return * 100)} / Sharpe ${leadBacktest.sharpe.toFixed(2)}`
        : "N/A",
      tone: leadBacktest && leadBacktest.total_return > 0 ? "buy" : "hold",
      note: leadBacktest ? `${leadBacktest.trade_count} trades` : "No backtest snapshot",
    },
  ];

  return (
    <div className="overview-shell">
      <section className="market-hero">
        <div className="market-hero-copy">
          <span className="eyebrow">Market Research Desk</span>
          <h1>Search a stock, inspect the candles, and decide if the buy thesis is real.</h1>
          <p>
            This workspace puts price structure first: market candles in the center, ranked buy ideas on the side,
            and the model or backtest context underneath the chart instead of hiding it in secondary pages.
          </p>
        </div>

        <div className="hero-action-panel">
          <span className="metric-label">Current buy focus</span>
          <strong>{selectedSymbol}</strong>
          <p>{getOpportunityLabel(selectedSignal, convictionScore)}</p>
          <div className="hero-score">
            <span>Conviction score</span>
            <strong>{convictionScore}/100</strong>
          </div>
        </div>
      </section>

      <section className="summary-ribbon">
        {summaryFocus.map((card) => (
          <article className="ribbon-card" key={card.label}>
            <span>{card.label}</span>
            <strong>
              {typeof card.value === "number"
                ? card.label.includes("Rate") || card.label.includes("Drawdown")
                  ? formatPercent(card.value)
                  : formatCurrency(card.value)
                : card.value}
            </strong>
            {typeof card.delta === "number" ? <small>{formatCurrency(card.delta)}</small> : null}
          </article>
        ))}
      </section>

      <section className="research-toolbar panel">
        <div>
          <span className="metric-label">Ticker Search</span>
          <h3>Research a new symbol before you buy</h3>
        </div>

        <form className="symbol-search" onSubmit={handleSymbolSubmit}>
          <input
            aria-label="Symbol"
            className="symbol-input"
            value={symbolInput}
            onChange={(event) => setSymbolInput(event.target.value)}
            placeholder="Type AAPL, NVDA, MSFT..."
          />
          <button className="primary-button" type="submit">
            Load market
          </button>
        </form>

        <div className="timeframe-strip" role="tablist" aria-label="Timeframe">
          {timeframeOptions.map((option) => (
            <button
              key={option}
              className={`timeframe-chip ${timeframe === option ? "active" : ""}`}
              onClick={() => setTimeframe(option)}
              type="button"
            >
              {option}
            </button>
          ))}
        </div>

        <div className="watchlist-strip">
          {rankedSignals.slice(0, 5).map((signal) => (
            <button
              key={`${signal.symbol}-${signal.timestamp}`}
              className={`watchlist-card ${selectedSymbol === signal.symbol ? "active" : ""}`}
              onClick={() => {
                setSelectedSymbol(signal.symbol);
                setSymbolInput(signal.symbol);
              }}
              type="button"
            >
              <span>{signal.symbol}</span>
              <strong>{signal.signal_type}</strong>
              <small>{((signal.confidence ?? 0) * 100).toFixed(0)}% confidence</small>
            </button>
          ))}
        </div>
      </section>

      <section className="research-grid">
        <article className="panel chart-stage">
          <div className="panel-header">
            <div>
              <h3>{selectedSymbol} market structure</h3>
              <p>
                {marketLoading
                  ? "Loading the latest candles for this symbol."
                  : latestBar
                  ? `${formatDateTime(latestBar.timestamp)} | Range ${formatCurrency(rangeLow)} to ${formatCurrency(rangeHigh)}`
                  : "No market structure loaded yet."}
              </p>
            </div>
            <div className="chart-stage-stats">
              <span>Avg volume {averageVolume > 0 ? averageVolume.toFixed(0) : "-"}</span>
              <span>{barsSource}</span>
            </div>
          </div>

          {marketError ? <div className="inline-alert">{marketError}</div> : null}
          <CandlestickChart bars={bars} symbol={selectedSymbol} sourceLabel={barsSource} />
        </article>

        <aside className="panel research-sidebar">
          <div className="panel-header">
            <div>
              <h3>Buy research brief</h3>
              <p>Signal, model and backtest context for the current symbol.</p>
            </div>
          </div>

          <div className="research-score-card">
            <span className="metric-label">Suggested action</span>
            <strong>{getOpportunityLabel(selectedSignal, convictionScore)}</strong>
            <p>
              {selectedSignal?.reason ??
                "No explicit rationale stored for this symbol. Use the candle structure and model context below."}
            </p>
          </div>

          <div className="research-checklist">
            {researchRows.map((row) => (
              <div className="check-row" key={row.label}>
                <div>
                  <span className="metric-label">{row.label}</span>
                  <strong>{row.value}</strong>
                </div>
                <div className={`research-note ${row.tone}`}>{row.note}</div>
              </div>
            ))}
          </div>

          <div className="buy-candidate-list">
            <div className="panel-header">
              <h3>Stocks to research now</h3>
              <p>Ranked directly from the latest signal tape.</p>
            </div>
            {rankedSignals.slice(0, 6).map((signal) => (
              <button
                className="candidate-row"
                key={`${signal.symbol}-${signal.timestamp}-research`}
                onClick={() => {
                  setSelectedSymbol(signal.symbol);
                  setSymbolInput(signal.symbol);
                }}
                type="button"
              >
                <div>
                  <strong>{signal.symbol}</strong>
                  <small>{formatDateTime(signal.timestamp)}</small>
                </div>
                <div>
                  <span className={`signal-pill ${signal.signal_type.toLowerCase()}`}>{signal.signal_type}</span>
                  <small>{((signal.confidence ?? 0) * 100).toFixed(1)}%</small>
                </div>
              </button>
            ))}
          </div>
        </aside>
      </section>

      <section className="lower-grid">
        <article className="panel">
          <div className="panel-header">
            <h3>Actionable signal tape</h3>
            <p>Shortlist for buy-side research, pulled from the latest generated outputs.</p>
          </div>
          <DataTable
            columns={["Symbol", "Bias", "Confidence", "Why it matters", "Time"]}
            rows={rankedSignals.slice(0, 8).map((signal) => [
              signal.symbol,
              <span className={`signal-pill ${signal.signal_type.toLowerCase()}`} key={`${signal.symbol}-bias`}>
                {signal.signal_type}
              </span>,
              `${((signal.confidence ?? 0) * 100).toFixed(1)}%`,
              signal.reason ?? "Research this chart for confirmation.",
              formatDateTime(signal.timestamp),
            ])}
          />
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Portfolio confirmation</h3>
            <p>Equity curve stays visible so buy ideas remain tied to real system behavior.</p>
          </div>
          <LineChart
            data={(snapshot?.equity_curve ?? []).map((point) => ({
              timestamp: point.timestamp,
              value: point.equity ?? 0,
            }))}
            stroke="#76f9b5"
            formatValue={formatCurrency}
          />
        </article>
      </section>

      {(loading || error) && !snapshot ? (
        <section className="panel page-panel">
          <div className="empty-state">{loading ? "Loading dashboard snapshot..." : error}</div>
        </section>
      ) : null}
    </div>
  );
}

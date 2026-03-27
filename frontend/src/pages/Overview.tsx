import { type FormEvent, useEffect, useState } from "react";

import { fetchMarketBars, fetchMarketPreview } from "../api/client";
import { DataTable } from "../components/DataTable";
import { BarChart } from "../components/charts/BarChart";
import { CandlestickChart } from "../components/charts/CandlestickChart";
import { LineChart } from "../components/charts/LineChart";
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

  const marketPulse = [
    {
      label: "Latest close",
      value: latestBar ? formatCurrency(latestBar.close) : "-",
      note: latestBar ? formatDateTime(latestBar.timestamp) : "Waiting for bars",
    },
    {
      label: "Session range",
      value: bars.length > 0 ? `${formatCurrency(rangeLow)} to ${formatCurrency(rangeHigh)}` : "-",
      note: barsSource,
    },
    {
      label: "Average volume",
      value: averageVolume > 0 ? averageVolume.toFixed(0) : "-",
      note: `Across ${bars.length || 0} candles`,
    },
    {
      label: "Backtest leader",
      value: leadBacktest ? leadBacktest.name : "No run",
      note: leadBacktest ? `Sharpe ${leadBacktest.sharpe.toFixed(2)}` : "Generate a run to compare",
    },
  ];

  const decisionCards = [
    {
      label: "Lead model",
      value: leadModel ? leadModel.name : "No model",
      note: leadModel ? `ROC-AUC ${leadModel.roc_auc.toFixed(2)} / F1 ${leadModel.f1.toFixed(2)}` : "Train models first",
    },
    {
      label: "Signal tape",
      value: `${rankedSignals.length} names`,
      note: rankedSignals.length > 0 ? `${rankedSignals[0].symbol} is currently leading` : "No recent signals",
    },
    {
      label: "Research stance",
      value: getOpportunityLabel(selectedSignal, convictionScore),
      note: selectedSignal?.reason ?? "Use the candle structure and context cards before simulating a trade.",
    },
    {
      label: "Snapshot age",
      value: formatDateTime(snapshot?.generated_at),
      note: "Latest stored dashboard snapshot",
    },
  ];

  return (
    <div className="dashboard-page">
      <section className="panel market-toolbar">
        <div className="toolbar-intro">
          <div>
            <span className="eyebrow">Buy-side workspace</span>
            <h2>Search a ticker and validate the setup before simulating the order.</h2>
            <p>
              This overview keeps the price structure in the center and pushes signals, model strength, and backtest
              context into the same decision surface.
            </p>
          </div>

          <div className="focus-summary">
            <span className="metric-label">Current focus</span>
            <strong>{selectedSymbol}</strong>
            <p>{getOpportunityLabel(selectedSignal, convictionScore)}</p>
            <div className="focus-summary-score">
              <span>Conviction</span>
              <strong>{convictionScore}/100</strong>
            </div>
          </div>
        </div>

        <div className="toolbar-actions-grid">
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

      <section className="dashboard-grid dashboard-grid-primary">
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
              <span>{barsSource}</span>
              <span>{averageVolume > 0 ? `Avg volume ${averageVolume.toFixed(0)}` : "No volume yet"}</span>
            </div>
          </div>

          {marketError ? <div className="inline-alert">{marketError}</div> : null}
          <CandlestickChart bars={bars} symbol={selectedSymbol} sourceLabel={barsSource} />
        </article>

        <aside className="research-sidebar">
          <section className="panel research-score-card">
            <span className="metric-label">Suggested action</span>
            <strong>{getOpportunityLabel(selectedSignal, convictionScore)}</strong>
            <p>
              {selectedSignal?.reason ??
                "No explicit rationale is stored for this symbol yet. Use the price structure and cross-check the model and backtest context below."}
            </p>

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
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h3>Market pulse</h3>
                <p>Quick context from the loaded candle window and stored research outputs.</p>
              </div>
            </div>
            <div className="insight-grid">
              {marketPulse.map((item) => (
                <div className="insight-card" key={item.label}>
                  <span className="metric-label">{item.label}</span>
                  <strong>{item.value}</strong>
                  <small>{item.note}</small>
                </div>
              ))}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h3>Research shortlist</h3>
                <p>Names at the top of the latest signal tape.</p>
              </div>
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
          </section>
        </aside>
      </section>

      <section className="dashboard-grid dashboard-grid-secondary">
        <article className="panel">
          <div className="panel-header">
            <div>
              <h3>Actionable signal tape</h3>
              <p>Shortlist for current buy-side research decisions.</p>
            </div>
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
            <div>
              <h3>Equity confirmation</h3>
              <p>Keep the research tape tied to actual stored system behavior.</p>
            </div>
          </div>
          <LineChart
            data={(snapshot?.equity_curve ?? []).map((point) => ({
              timestamp: point.timestamp,
              value: point.equity ?? 0,
            }))}
            stroke="#2563eb"
            formatValue={formatCurrency}
          />
        </article>
      </section>

      <section className="dashboard-grid dashboard-grid-secondary">
        <article className="panel">
          <div className="panel-header">
            <div>
              <h3>Win / loss distribution</h3>
              <p>Distribution of stored strategy outcomes from the current dashboard snapshot.</p>
            </div>
          </div>
          <BarChart data={snapshot?.win_loss_distribution ?? []} />
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <h3>Decision context</h3>
              <p>Model, signal, and timestamp markers to keep the thesis grounded.</p>
            </div>
          </div>
          <div className="insight-grid">
            {decisionCards.map((item) => (
              <div className="insight-card" key={item.label}>
                <span className="metric-label">{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.note}</small>
              </div>
            ))}
          </div>
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

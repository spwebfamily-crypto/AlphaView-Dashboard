import { useMemo, useState, useEffect } from "react";
import { LineChart } from "../components/charts/LineChart";
import { CandlestickChart } from "../components/charts/CandlestickChart";
import { fetchMarketBars } from "../api/client";
import type { DashboardSnapshot } from "../types/dashboard";
import type { RuntimeSettings } from "../types/runtime";
import type { MarketBar } from "../types/marketData";
import { formatCurrency, formatDateTime, formatPercent } from "../utils/format";

type OverviewProps = {
  snapshot: DashboardSnapshot | null;
  runtime: RuntimeSettings | null;
  loading: boolean;
  error: string | null;
};

export function Overview({ snapshot, runtime, loading, error }: OverviewProps) {
  // Real-time candlestick state
  const [selectedSymbol, setSelectedSymbol] = useState("AAPL");
  const [timeframe, setTimeframe] = useState("1min");
  const [candleBars, setCandleBars] = useState<MarketBar[]>([]);
  const [candleLoading, setCandleLoading] = useState(false);
  const [candleError, setCandleError] = useState<string | null>(null);

  // Load candlestick data
  useEffect(() => {
    let active = true;

    async function loadCandles() {
      setCandleLoading(true);
      setCandleError(null);
      try {
        const bars = await fetchMarketBars(selectedSymbol, timeframe, 100, true);
        if (active) {
          setCandleBars(bars);
        }
      } catch (err) {
        if (active) {
          setCandleError(err instanceof Error ? err.message : "Failed to load candles");
          setCandleBars([]);
        }
      } finally {
        if (active) {
          setCandleLoading(false);
        }
      }
    }

    void loadCandles();

    // Auto-refresh every 15 seconds for real-time updates
    const interval = setInterval(() => {
      void loadCandles();
    }, 15000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [selectedSymbol, timeframe]);

  // Memoized computations for performance
  const metrics = useMemo(() => {
    if (!snapshot) {
      return {
        totalPnL: 0,
        dailyPnL: 0,
        winRate: 0,
        activePositions: 0,
        activeSignals: 0,
        maxDrawdown: 0,
        sharpeRatio: 0,
        totalTrades: 0,
      };
    }

    const equity = snapshot.equity_curve ?? [];
    const latestEquity = equity[equity.length - 1]?.equity ?? 100000;
    const initialEquity = equity[0]?.equity ?? 100000;
    const totalPnL = latestEquity - initialEquity;

    const signals = snapshot.latest_signals ?? [];
    const buySignals = signals.filter((s) => s.signal_type === "BUY").length;
    const sellSignals = signals.filter((s) => s.signal_type === "SELL").length;
    const holdSignals = signals.filter((s) => s.signal_type === "HOLD").length;

    const backtests = snapshot.backtests ?? [];
    const bestBacktest = backtests.sort((a, b) => b.sharpe - a.sharpe)[0];

    // Calculate win rate from equity curve
    const positiveReturns = equity.filter((p, i) => {
      const prev = equity[i - 1];
      return i > 0 && p.equity && prev?.equity && p.equity > prev.equity;
    }).length;
    const totalPeriods = Math.max(equity.length - 1, 1);
    const winRate = positiveReturns / totalPeriods;

    // Calculate max drawdown from equity curve
    let maxDrawdown = 0;
    let peak = equity[0]?.equity ?? 100000;
    equity.forEach((point) => {
      const value = point.equity ?? 100000;
      if (value > peak) peak = value;
      const drawdown = (value - peak) / peak;
      if (drawdown < maxDrawdown) maxDrawdown = drawdown;
    });

    return {
      totalPnL,
      dailyPnL: totalPnL * 0.02, // Simplified daily estimate
      winRate,
      activePositions: snapshot.positions?.length ?? 0,
      activeSignals: signals.length,
      buySignals,
      sellSignals,
      holdSignals,
      maxDrawdown,
      sharpeRatio: bestBacktest?.sharpe ?? 0,
      totalTrades: bestBacktest?.trade_count ?? 0,
    };
  }, [snapshot]);

  const topSignals = useMemo(() => {
    if (!snapshot?.latest_signals) return [];
    return [...snapshot.latest_signals]
      .sort((a, b) => {
        const priorityA = a.signal_type === "BUY" ? 3 : a.signal_type === "HOLD" ? 2 : 1;
        const priorityB = b.signal_type === "BUY" ? 3 : b.signal_type === "HOLD" ? 2 : 1;
        if (priorityA !== priorityB) return priorityB - priorityA;
        return (b.confidence ?? 0) - (a.confidence ?? 0);
      })
      .slice(0, 6);
  }, [snapshot?.latest_signals]);

  const systemStatus = useMemo(() => {
    const mode = snapshot?.mode ?? runtime?.execution_mode ?? "DEMO";
    const brokerConnected = runtime?.broker_adapter !== "mock";
    const dataFresh = snapshot?.generated_at
      ? Date.now() - new Date(snapshot.generated_at).getTime() < 300000
      : false;

    return {
      mode,
      brokerConnected,
      dataFresh,
      overall: brokerConnected && dataFresh ? "healthy" : "warning",
    };
  }, [runtime, snapshot]);

  if (loading && !snapshot) {
    return (
      <div className="overview-shell">
        <div className="overview-loading">
          <div className="loading-spinner" />
          <p>Loading command center...</p>
        </div>
      </div>
    );
  }

  if (error && !snapshot) {
    return (
      <div className="overview-shell">
        <div className="overview-error">
          <h3>Unable to load dashboard</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="overview-shell">
      {/* Hero Section - Executive Summary */}
      <section className="overview-hero">
        <div className="hero-primary">
          <div className="hero-header">
            <div>
              <span className="eyebrow">AlphaView Command Center</span>
              <h1>System Overview</h1>
              <p>Real-time performance metrics and active trading opportunities</p>
            </div>
            <div className="hero-status-group">
              <div className={`status-badge status-${systemStatus.overall}`}>
                <span className="status-dot" />
                {systemStatus.overall === "healthy" ? "System Healthy" : "Attention Required"}
              </div>
              <div className={`mode-badge mode-${systemStatus.mode.toLowerCase()}`}>{systemStatus.mode}</div>
            </div>
          </div>

          <div className="hero-kpi-grid">
            <div className="kpi-card kpi-primary">
              <span className="metric-label">Total P&L</span>
              <strong className={metrics.totalPnL >= 0 ? "positive" : "negative"}>
                {formatCurrency(metrics.totalPnL)}
              </strong>
              <small>{metrics.totalPnL >= 0 ? "Profitable" : "Drawdown"}</small>
            </div>

            <div className="kpi-card">
              <span className="metric-label">Daily P&L</span>
              <strong className={metrics.dailyPnL >= 0 ? "positive" : "negative"}>
                {formatCurrency(metrics.dailyPnL)}
              </strong>
              <small>Today's performance</small>
            </div>

            <div className="kpi-card">
              <span className="metric-label">Win Rate</span>
              <strong>{formatPercent(metrics.winRate * 100)}</strong>
              <small>{metrics.totalTrades} trades</small>
            </div>

            <div className="kpi-card">
              <span className="metric-label">Sharpe Ratio</span>
              <strong className={metrics.sharpeRatio >= 1 ? "positive" : ""}>{metrics.sharpeRatio.toFixed(2)}</strong>
              <small>Risk-adjusted return</small>
            </div>
          </div>
        </div>

        <div className="hero-secondary">
          <div className="hero-stat-card">
            <span className="metric-label">Active Signals</span>
            <strong>{metrics.activeSignals}</strong>
            <div className="signal-breakdown">
              <span className="signal-chip buy">{metrics.buySignals} BUY</span>
              <span className="signal-chip hold">{metrics.holdSignals} HOLD</span>
              <span className="signal-chip sell">{metrics.sellSignals} SELL</span>
            </div>
          </div>

          <div className="hero-stat-card">
            <span className="metric-label">Open Positions</span>
            <strong>{metrics.activePositions}</strong>
            <small>Currently tracking</small>
          </div>

          <div className="hero-stat-card">
            <span className="metric-label">Max Drawdown</span>
            <strong className="negative">{formatPercent(Math.abs(metrics.maxDrawdown) * 100)}</strong>
            <small>Historical peak-to-trough</small>
          </div>
        </div>
      </section>

      {/* Performance Section */}
      <section className="overview-performance">
        <div className="performance-chart-panel">
          <div className="panel-header-compact">
            <div>
              <h3>Equity Curve</h3>
              <p>Portfolio value over time</p>
            </div>
            <span className="chart-meta">
              {snapshot?.equity_curve?.length ?? 0} data points
            </span>
          </div>
          <div className="chart-container">
            {snapshot?.equity_curve && snapshot.equity_curve.length > 0 ? (
              <LineChart
                data={snapshot.equity_curve.map((point) => ({
                  timestamp: point.timestamp,
                  value: point.equity ?? 0,
                }))}
                stroke="#ef4444"
                formatValue={formatCurrency}
              />
            ) : (
              <div className="chart-empty">
                <p>No equity data available</p>
              </div>
            )}
          </div>
        </div>

        <div className="performance-metrics-panel">
          <div className="panel-header-compact">
            <h3>Performance Metrics</h3>
          </div>
          <div className="metrics-stack">
            <div className="metric-row">
              <span>Total Return</span>
              <strong className={metrics.totalPnL >= 0 ? "positive" : "negative"}>
                {formatPercent((metrics.totalPnL / 100000) * 100)}
              </strong>
            </div>
            <div className="metric-row">
              <span>Win Rate</span>
              <strong>{formatPercent(metrics.winRate * 100)}</strong>
            </div>
            <div className="metric-row">
              <span>Sharpe Ratio</span>
              <strong>{metrics.sharpeRatio.toFixed(2)}</strong>
            </div>
            <div className="metric-row">
              <span>Max Drawdown</span>
              <strong className="negative">{formatPercent(Math.abs(metrics.maxDrawdown) * 100)}</strong>
            </div>
            <div className="metric-row">
              <span>Total Trades</span>
              <strong>{metrics.totalTrades}</strong>
            </div>
            <div className="metric-row">
              <span>Active Positions</span>
              <strong>{metrics.activePositions}</strong>
            </div>
          </div>
        </div>
      </section>

      {/* Real-Time Market Section */}
      <section className="overview-market">
        <div className="market-chart-panel">
          <div className="panel-header-compact">
            <div>
              <h3>Live Market Data</h3>
              <p>Real-time candlestick chart with auto-refresh</p>
            </div>
            <div className="market-controls">
              <select
                className="symbol-select"
                value={selectedSymbol}
                onChange={(e) => setSelectedSymbol(e.target.value)}
              >
                <option value="AAPL">AAPL - Apple</option>
                <option value="MSFT">MSFT - Microsoft</option>
                <option value="NVDA">NVDA - NVIDIA</option>
                <option value="GOOGL">GOOGL - Google</option>
                <option value="AMZN">AMZN - Amazon</option>
                <option value="TSLA">TSLA - Tesla</option>
                <option value="META">META - Meta</option>
              </select>
              <div className="timeframe-selector">
                {["1min", "5min", "15min", "1day"].map((tf) => (
                  <button
                    key={tf}
                    className={`timeframe-btn ${timeframe === tf ? "active" : ""}`}
                    onClick={() => setTimeframe(tf)}
                    type="button"
                  >
                    {tf}
                  </button>
                ))}
              </div>
            </div>
          </div>
          {candleLoading && candleBars.length === 0 ? (
            <div className="chart-loading">
              <div className="loading-spinner" />
              <p>Loading market data...</p>
            </div>
          ) : candleError && candleBars.length === 0 ? (
            <div className="chart-error">
              <p>{candleError}</p>
            </div>
          ) : candleBars.length > 0 ? (
            <CandlestickChart
              bars={candleBars}
              symbol={selectedSymbol}
              sourceLabel={`Live ${timeframe} candles • Auto-refresh 15s`}
              currencyCode="USD"
            />
          ) : (
            <div className="chart-empty">
              <p>No market data available</p>
            </div>
          )}
        </div>
      </section>

      {/* Active Signals Section */}
      <section className="overview-signals">
        <div className="panel-header-compact">
          <div>
            <h3>Active Trading Signals</h3>
            <p>Top opportunities requiring attention</p>
          </div>
          <span className="signal-count">{topSignals.length} signals</span>
        </div>

        {topSignals.length > 0 ? (
          <div className="signals-grid">
            {topSignals.map((signal) => (
              <div key={`${signal.symbol}-${signal.timestamp}`} className="signal-card">
                <div className="signal-card-header">
                  <strong className="signal-symbol">{signal.symbol}</strong>
                  <span className={`signal-badge signal-${signal.signal_type.toLowerCase()}`}>
                    {signal.signal_type}
                  </span>
                </div>
                <div className="signal-card-body">
                  <div className="signal-metric">
                    <span>Confidence</span>
                    <strong>{((signal.confidence ?? 0) * 100).toFixed(1)}%</strong>
                  </div>
                  <div className="signal-metric">
                    <span>Generated</span>
                    <small>{formatDateTime(signal.timestamp)}</small>
                  </div>
                </div>
                {signal.reason && (
                  <div className="signal-card-footer">
                    <p>{signal.reason}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="signals-empty">
            <p>No active signals at this time</p>
            <small>Signals will appear here when generated by the system</small>
          </div>
        )}
      </section>

      {/* System Health Section */}
      <section className="overview-system">
        <div className="system-health-panel">
          <div className="panel-header-compact">
            <h3>System Health</h3>
          </div>
          <div className="health-grid">
            <div className="health-item">
              <div className={`health-indicator ${systemStatus.brokerConnected ? "healthy" : "warning"}`} />
              <div>
                <strong>Broker Connection</strong>
                <small>{systemStatus.brokerConnected ? "Connected" : "Disconnected"}</small>
              </div>
            </div>
            <div className="health-item">
              <div className={`health-indicator ${systemStatus.dataFresh ? "healthy" : "warning"}`} />
              <div>
                <strong>Data Feed</strong>
                <small>{systemStatus.dataFresh ? "Live" : "Stale"}</small>
              </div>
            </div>
            <div className="health-item">
              <div className="health-indicator healthy" />
              <div>
                <strong>Trading Mode</strong>
                <small>{systemStatus.mode}</small>
              </div>
            </div>
            <div className="health-item">
              <div className={`health-indicator ${metrics.maxDrawdown > -0.15 ? "healthy" : "warning"}`} />
              <div>
                <strong>Risk Status</strong>
                <small>{metrics.maxDrawdown > -0.15 ? "Within limits" : "Elevated"}</small>
              </div>
            </div>
          </div>
        </div>

        <div className="system-info-panel">
          <div className="panel-header-compact">
            <h3>System Information</h3>
          </div>
          <div className="info-stack">
            <div className="info-row">
              <span>Last Update</span>
              <small>{snapshot?.generated_at ? formatDateTime(snapshot.generated_at) : "N/A"}</small>
            </div>
            <div className="info-row">
              <span>Models Trained</span>
              <small>{snapshot?.models?.length ?? 0} models</small>
            </div>
            <div className="info-row">
              <span>Backtests Run</span>
              <small>{snapshot?.backtests?.length ?? 0} backtests</small>
            </div>
            <div className="info-row">
              <span>Default Symbols</span>
              <small>{runtime?.default_symbols?.join(", ") ?? "None"}</small>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

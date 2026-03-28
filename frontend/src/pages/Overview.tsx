import { type FormEvent, useDeferredValue, useEffect, useState } from "react";

import { fetchLiveMarketUniverse, fetchMarketBars, fetchMarketPreview } from "../api/client";
import { DataTable } from "../components/DataTable";
import { BarChart } from "../components/charts/BarChart";
import { CandlestickChart } from "../components/charts/CandlestickChart";
import { LineChart } from "../components/charts/LineChart";
import type { DashboardBacktest, DashboardModel, DashboardSnapshot, LatestSignal } from "../types/dashboard";
import type { MarketBar, TrackedSymbol } from "../types/marketData";
import type { RuntimeSettings } from "../types/runtime";
import { formatCurrency, formatDateTime, formatPercent } from "../utils/format";

type OverviewProps = {
  snapshot: DashboardSnapshot | null;
  runtime: RuntimeSettings | null;
  loading: boolean;
  error: string | null;
};

type MarketRegion = "EUR" | "USD";

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

function getMarketKey(symbol: TrackedSymbol) {
  return symbol.primary_exchange?.trim().toUpperCase() || symbol.exchange?.trim().toUpperCase() || "WATCHLIST";
}

function getMarketLabel(market: string) {
  if (market === "ALL") {
    return "All markets";
  }
  if (market === "WATCHLIST") {
    return "Watchlist";
  }
  return market;
}

function mergeSymbolUniverse(trackedSymbols: TrackedSymbol[], fallbackTickers: string[]) {
  const merged = new Map<string, TrackedSymbol>();

  trackedSymbols.forEach((symbol) => {
    merged.set(symbol.ticker.toUpperCase(), { ...symbol, ticker: symbol.ticker.toUpperCase() });
  });

  fallbackTickers.forEach((ticker) => {
    const normalized = getNormalizedSymbol(ticker);
    if (!normalized || merged.has(normalized)) {
      return;
    }

    merged.set(normalized, {
      ticker: normalized,
      name: normalized,
      exchange: "WATCHLIST",
      asset_type: "equity",
      is_active: true,
    });
  });

  return [...merged.values()].sort((left, right) => {
    const marketCompare = getMarketKey(left).localeCompare(getMarketKey(right));
    if (marketCompare !== 0) {
      return marketCompare;
    }
    return left.ticker.localeCompare(right.ticker);
  });
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

function formatLiveMove(symbol: TrackedSymbol) {
  if (symbol.change_percent == null) {
    return symbol.quote_timestamp ? `Updated ${formatDateTime(symbol.quote_timestamp)}` : "Quote unavailable";
  }
  const prefix = symbol.change_percent >= 0 ? "+" : "";
  const changeValue = symbol.change != null ? ` (${prefix}${formatCurrency(symbol.change, symbol.currency)})` : "";
  return `${prefix}${symbol.change_percent.toFixed(2)}%${changeValue}`;
}

function getLotLabel(symbol: TrackedSymbol) {
  const lotSize = symbol.round_lot_size ?? 100;
  if (symbol.last_price == null) {
    return `Round lot ${lotSize} sh`;
  }
  return `${lotSize} sh lot ${formatCurrency(symbol.last_price * lotSize, symbol.currency)}`;
}

function getUniverseRequest(region: MarketRegion) {
  if (region === "EUR") {
    return {
      label: "Europe market",
      metricLabel: "Europe equity universe",
      locale: "global",
      currency: "EUR",
      placeholder: "Search SAP, AIR, OR, MC, XPAR...",
      description:
        "Browse European exchanges through EODHD. Quotes come from EODHD, daily candles can sync from EODHD, and intraday candles still depend on IBKR Gateway or TWS.",
    };
  }

  return {
    label: "US market",
    metricLabel: "Live US equity universe",
    locale: "us",
    currency: undefined,
    placeholder: "Search Apple, AAPL, Tesla, XNYS...",
    description:
      "Browse the real provider universe, load a name into the candlestick stage, and keep quotes refreshing while the page stays open.",
  };
}

export function Overview({ snapshot, runtime, loading, error }: OverviewProps) {
  const rankedSignals = getSortedSignals(snapshot?.latest_signals ?? []);
  const leadModel = getLeadModel(snapshot?.models ?? []);
  const leadBacktest = getLeadBacktest(snapshot?.backtests ?? []);
  const defaultSymbol = rankedSignals[0]?.symbol ?? runtime?.default_symbols[0] ?? "SAP.DE";

  const [symbolInput, setSymbolInput] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [timeframe, setTimeframe] = useState("");
  const [bars, setBars] = useState<MarketBar[]>([]);
  const [barsSource, setBarsSource] = useState("historical bars");
  const [marketLoading, setMarketLoading] = useState(false);
  const [marketError, setMarketError] = useState<string | null>(null);
  const [marketUniverseItems, setMarketUniverseItems] = useState<TrackedSymbol[]>([]);
  const [marketQuery, setMarketQuery] = useState("");
  const [marketRegion, setMarketRegion] = useState<MarketRegion>("EUR");
  const [selectedMarket, setSelectedMarket] = useState("ALL");
  const [universeCursor, setUniverseCursor] = useState<string | null>(null);
  const [universeSource, setUniverseSource] = useState("eodhd-europe-exchanges");
  const [universeAsOf, setUniverseAsOf] = useState<string | null>(null);
  const [universeLoading, setUniverseLoading] = useState(false);
  const [universeError, setUniverseError] = useState<string | null>(null);
  const deferredMarketQuery = useDeferredValue(marketQuery.trim());
  const universeRequest = getUniverseRequest(marketRegion);

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
    setSelectedMarket("ALL");
  }, [marketRegion]);

  useEffect(() => {
    if (marketUniverseItems.length === 0) {
      return;
    }
    if (marketRegion !== "EUR") {
      return;
    }
    if (selectedSymbol && selectedSymbol !== defaultSymbol) {
      return;
    }
    if (marketUniverseItems.some((symbol) => symbol.ticker === selectedSymbol)) {
      return;
    }
    const nextTicker = marketUniverseItems[0]?.ticker;
    if (!nextTicker) {
      return;
    }
    setSelectedSymbol(nextTicker);
    setSymbolInput(nextTicker);
  }, [defaultSymbol, marketRegion, marketUniverseItems, selectedSymbol]);

  useEffect(() => {
    let active = true;

    async function loadUniverse() {
      setUniverseLoading(true);
      try {
        const payload = await fetchLiveMarketUniverse({
          locale: universeRequest.locale,
          exchange: selectedMarket === "ALL" ? undefined : selectedMarket,
          query: deferredMarketQuery || undefined,
          limit: 24,
          securityType: "CS",
          currency: universeRequest.currency,
          includeQuotes: true,
        });
        if (!active) {
          return;
        }
        setMarketUniverseItems(payload.items);
        setUniverseCursor(payload.next_cursor);
        setUniverseSource(payload.source);
        setUniverseAsOf(payload.as_of);
        setUniverseError(null);
      } catch (caughtError) {
        if (!active) {
          return;
        }
        setMarketUniverseItems([]);
        setUniverseCursor(null);
        setUniverseError(caughtError instanceof Error ? caughtError.message : "Unable to load the live market universe.");
      } finally {
        if (active) {
          setUniverseLoading(false);
        }
      }
    }

    void loadUniverse();

    const refreshHandle = window.setInterval(() => {
      void loadUniverse();
    }, 30000);

    return () => {
      active = false;
      window.clearInterval(refreshHandle);
    };
  }, [deferredMarketQuery, selectedMarket, snapshot?.generated_at, universeRequest.currency, universeRequest.locale]);

  useEffect(() => {
    if (!selectedSymbol || !timeframe) {
      return;
    }

    let active = true;

    async function loadBars() {
      setMarketLoading(true);
      setMarketError(null);

      try {
        const historicalBars = await fetchMarketBars(selectedSymbol, timeframe, 72, true);
        if (!active) {
          return;
        }

        if (historicalBars.length > 0) {
          setBars(historicalBars);
          setBarsSource(
            marketRegion === "EUR"
              ? timeframe === "1day"
                ? "EODHD daily candles"
                : "IBKR or stored intraday candles"
              : "provider-synced candles",
          );
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
    const refreshHandle = window.setInterval(
      () => {
        void loadBars();
      },
      timeframe === "1day" ? 60000 : 15000,
    );

    return () => {
      active = false;
      window.clearInterval(refreshHandle);
    };
  }, [marketRegion, selectedSymbol, timeframe]);

  function handleSymbolSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = getNormalizedSymbol(symbolInput);
    if (normalized) {
      setSelectedSymbol(normalized);
      setSymbolInput(normalized);
    }
  }

  async function handleLoadMoreUniverse() {
    if (!universeCursor) {
      return;
    }

    try {
      setUniverseLoading(true);
      const payload = await fetchLiveMarketUniverse({
        locale: universeRequest.locale,
        exchange: selectedMarket === "ALL" ? undefined : selectedMarket,
        query: deferredMarketQuery || undefined,
        limit: 24,
        cursor: universeCursor,
        securityType: "CS",
        currency: universeRequest.currency,
        includeQuotes: true,
      });
      setMarketUniverseItems((current) => {
        const merged = new Map<string, TrackedSymbol>();
        [...current, ...payload.items].forEach((item) => {
          merged.set(item.ticker.toUpperCase(), item);
        });
        return [...merged.values()];
      });
      setUniverseCursor(payload.next_cursor);
      setUniverseSource(payload.source);
      setUniverseAsOf(payload.as_of);
      setUniverseError(null);
    } catch (caughtError) {
      setUniverseError(caughtError instanceof Error ? caughtError.message : "Unable to load more live symbols.");
    } finally {
      setUniverseLoading(false);
    }
  }

  const signalRanks = rankedSignals.reduce<Record<string, number>>((accumulator, signal, index) => {
    accumulator[signal.symbol] = index;
    return accumulator;
  }, {});

  const symbolUniverse = mergeSymbolUniverse(marketUniverseItems, [
    defaultSymbol,
    selectedSymbol,
    symbolInput,
    ...(runtime?.default_symbols ?? []),
    ...rankedSignals.map((signal) => signal.symbol),
  ]);
  const marketOptions = [
    "ALL",
    ...Array.from(new Set([selectedMarket, ...marketUniverseItems.map((symbol) => getMarketKey(symbol))]))
      .filter((market) => market && market !== "ALL")
      .sort((left, right) => left.localeCompare(right)),
  ];
  const marketOptionKey = marketOptions.join("|");
  const filteredUniverse = marketUniverseItems.filter(
    (symbol) => selectedMarket === "ALL" || getMarketKey(symbol) === selectedMarket,
  );
  const marketBrowserSymbols = [...filteredUniverse]
    .sort((left, right) => {
      if (left.ticker === selectedSymbol) {
        return -1;
      }
      if (right.ticker === selectedSymbol) {
        return 1;
      }

      const leftRank = signalRanks[left.ticker] ?? Number.MAX_SAFE_INTEGER;
      const rightRank = signalRanks[right.ticker] ?? Number.MAX_SAFE_INTEGER;
      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }

      return left.ticker.localeCompare(right.ticker);
    })
    .slice(0, 12);

  useEffect(() => {
    if (selectedMarket !== "ALL" && deferredMarketQuery && !marketOptionKey.split("|").includes(selectedMarket)) {
      setSelectedMarket("ALL");
    }
  }, [deferredMarketQuery, marketOptionKey, selectedMarket]);

  const selectedSignal =
    rankedSignals.find((signal) => signal.symbol === selectedSymbol) ?? rankedSignals[0] ?? null;
  const selectedUniverseSymbol =
    symbolUniverse.find((symbol) => symbol.ticker === selectedSymbol) ?? null;
  const selectedCurrencyCode = selectedUniverseSymbol?.currency ?? (marketRegion === "EUR" ? "EUR" : "USD");
  const requestedMarketNotice =
    marketRegion === "EUR" &&
    !universeLoading &&
    !universeError &&
    (
      universeSource === "eodhd-watchlist-fallback" ||
      universeSource === "eodhd-search-fallback" ||
      universeSource === "ibkr-search-fallback" ||
      universeSource === "ibkr-symbol-search-fallback" ||
      (marketUniverseItems.length === 0 && !deferredMarketQuery)
    )
      ? "Configure EODHD_API_TOKEN para carregar acoes europeias e cotacoes reais. Para candles intraday, mantenha o IBKR Gateway/TWS ativo ou use timeframe 1day."
      : null;
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
      value: latestBar ? formatCurrency(latestBar.close, selectedCurrencyCode) : "-",
      note: latestBar ? formatDateTime(latestBar.timestamp) : "Waiting for bars",
    },
    {
      label: "Session range",
      value:
        bars.length > 0
          ? `${formatCurrency(rangeLow, selectedCurrencyCode)} to ${formatCurrency(rangeHigh, selectedCurrencyCode)}`
          : "-",
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
              list="tracked-market-symbols"
              value={symbolInput}
              onChange={(event) => setSymbolInput(event.target.value)}
              placeholder={marketRegion === "EUR" ? "Type SAP.DE, MC.PA, AIR.PA..." : "Type AAPL, NVDA, MSFT..."}
            />
            <button className="primary-button" type="submit">
              Load market
            </button>
          </form>
          <datalist id="tracked-market-symbols">
            {filteredUniverse.slice(0, 200).map((symbol) => (
              <option key={`${symbol.ticker}-option`} value={symbol.ticker}>
                {symbol.name ?? symbol.ticker} | {getMarketLabel(getMarketKey(symbol))}
              </option>
            ))}
          </datalist>

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

        <div className="market-browser">
          <div className="market-browser-header">
            <div>
              <span className="metric-label">{universeRequest.metricLabel}</span>
              <strong>{filteredUniverse.length} live symbols loaded for the candle chart</strong>
              <p>{universeRequest.description}</p>
            </div>
            <span className="market-browser-meta">
              {universeLoading
                ? "Refreshing live universe..."
                : `${universeRequest.label} | ${Math.max(0, marketOptions.length - 1)} markets | ${universeSource}`}
            </span>
          </div>

          {universeError ? <div className="inline-alert">{universeError}</div> : null}
          {requestedMarketNotice ? <div className="inline-alert">{requestedMarketNotice}</div> : null}

          <div className="market-filter-strip" role="tablist" aria-label="Market region">
            {(["EUR", "USD"] as const).map((region) => (
              <button
                key={region}
                className={`market-filter-chip ${marketRegion === region ? "active" : ""}`}
                onClick={() => setMarketRegion(region)}
                type="button"
              >
                {getUniverseRequest(region).label}
              </button>
            ))}
          </div>

          <div className="market-browser-search">
            <input
              aria-label="Live market search"
              className="symbol-input"
              onChange={(event) => setMarketQuery(event.target.value)}
              placeholder={universeRequest.placeholder}
              type="text"
              value={marketQuery}
            />
            <span className="market-browser-footnote">
              {universeAsOf ? `Provider sync ${formatDateTime(universeAsOf)}` : "Waiting for provider sync"}
            </span>
          </div>

          <div className="market-filter-strip" role="tablist" aria-label="Market filter">
            {marketOptions.map((market) => (
              <button
                key={market}
                className={`market-filter-chip ${selectedMarket === market ? "active" : ""}`}
                onClick={() => setSelectedMarket(market)}
                type="button"
              >
                {getMarketLabel(market)}
              </button>
            ))}
          </div>

          {marketBrowserSymbols.length > 0 ? (
            <div className="market-browser-grid">
              {marketBrowserSymbols.map((symbol) => (
                <button
                  key={`${symbol.ticker}-${getMarketKey(symbol)}`}
                  className={`market-browser-card ${selectedSymbol === symbol.ticker ? "active" : ""}`}
                  onClick={() => {
                    setSelectedSymbol(symbol.ticker);
                    setSymbolInput(symbol.ticker);
                  }}
                  type="button"
                >
                  <span>{getMarketLabel(getMarketKey(symbol))}</span>
                  <strong>{symbol.ticker}</strong>
                  <small>{symbol.name ?? "Live symbol"}</small>
                  <small className="market-browser-price">
                    {symbol.last_price != null ? formatCurrency(symbol.last_price, symbol.currency) : "Price unavailable"}
                  </small>
                  <small className={`market-browser-move ${(symbol.change_percent ?? 0) >= 0 ? "positive" : "negative"}`}>
                    {formatLiveMove(symbol)}
                  </small>
                  <small className="market-browser-lot">{getLotLabel(symbol)}</small>
                </button>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              {marketRegion === "EUR"
                ? "Nenhum simbolo europeu ficou disponivel. Refine a busca ou configure EODHD para universo/quotes e IBKR para candles intraday."
                : "No live symbols matched this filter yet. Refine the search or type a ticker above to load it manually."}
            </div>
          )}

          {filteredUniverse.length > marketBrowserSymbols.length ? (
            <div className="market-browser-footnote">
              Showing {marketBrowserSymbols.length} of {filteredUniverse.length} loaded names in{" "}
              {getMarketLabel(selectedMarket)}.
            </div>
          ) : null}

          {universeCursor ? (
            <div className="market-browser-actions">
              <button className="ghost-button" disabled={universeLoading} onClick={handleLoadMoreUniverse} type="button">
                {universeLoading ? "Loading more..." : `Load more ${marketRegion === "EUR" ? "Europe" : "live"} markets`}
              </button>
            </div>
          ) : null}
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
                    ? `${formatDateTime(latestBar.timestamp)} | Range ${formatCurrency(rangeLow, selectedCurrencyCode)} to ${formatCurrency(rangeHigh, selectedCurrencyCode)}`
                    : "No market structure loaded yet."}
              </p>
            </div>
            <div className="chart-stage-stats">
              <span>{barsSource}</span>
              <span>{timeframe === "1day" ? "Auto-refresh 60s" : "Auto-refresh 15s"}</span>
              <span>{averageVolume > 0 ? `Avg volume ${averageVolume.toFixed(0)}` : "No volume yet"}</span>
            </div>
          </div>

          {marketError ? <div className="inline-alert">{marketError}</div> : null}
          <CandlestickChart
            bars={bars}
            symbol={selectedSymbol}
            sourceLabel={barsSource}
            currencyCode={selectedCurrencyCode}
          />
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
              <span className="table-symbol" key={`${signal.symbol}-overview-symbol`}>
                {signal.symbol}
              </span>,
              <span className={`signal-pill ${signal.signal_type.toLowerCase()}`} key={`${signal.symbol}-bias`}>
                {signal.signal_type}
              </span>,
              `${((signal.confidence ?? 0) * 100).toFixed(1)}%`,
              signal.reason ?? "Research this chart for confirmation.",
              formatDateTime(signal.timestamp),
            ])}
            caption="Top-ranked research tape"
            footnote="Use this shortlist to decide what deserves chart review next. Signals remain research outputs, not trade guarantees."
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
            stroke="#9ca3af"
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

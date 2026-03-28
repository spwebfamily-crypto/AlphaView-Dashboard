import { useEffect, useState } from "react";

import type { MarketBar } from "../../types/marketData";
import { formatCurrency, formatDateTime } from "../../utils/format";

type CandlestickChartProps = {
  bars: MarketBar[];
  symbol: string;
  sourceLabel?: string;
  currencyCode?: string | null;
};

const DEFAULT_VISIBLE_BARS = 36;
const MIN_VISIBLE_BARS = 12;

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function getInitialVisibleCount(totalBars: number) {
  if (totalBars <= MIN_VISIBLE_BARS) {
    return totalBars;
  }
  return Math.min(DEFAULT_VISIBLE_BARS, totalBars);
}

function getY(value: number, min: number, max: number, height: number, top: number, bottom: number) {
  const range = max - min || 1;
  return top + ((max - value) / range) * (height - top - bottom);
}

export function CandlestickChart({ bars, symbol, sourceLabel, currencyCode }: CandlestickChartProps) {
  const initialVisibleCount = getInitialVisibleCount(bars.length);
  const [visibleCount, setVisibleCount] = useState(initialVisibleCount);
  const [windowStart, setWindowStart] = useState(Math.max(0, bars.length - initialVisibleCount));
  const [hoveredOffset, setHoveredOffset] = useState<number | null>(null);

  useEffect(() => {
    const nextVisibleCount = getInitialVisibleCount(bars.length);
    setVisibleCount(nextVisibleCount);
    setWindowStart(Math.max(0, bars.length - nextVisibleCount));
    setHoveredOffset(null);
  }, [bars.length, bars[0]?.timestamp, bars[bars.length - 1]?.timestamp, symbol]);

  if (bars.length === 0) {
    return <div className="empty-state">No candles available for {symbol}.</div>;
  }

  const minVisibleCount = Math.min(MIN_VISIBLE_BARS, bars.length);
  const safeVisibleCount = clamp(visibleCount, minVisibleCount, bars.length);
  const maxWindowStart = Math.max(0, bars.length - safeVisibleCount);
  const safeWindowStart = clamp(windowStart, 0, maxWindowStart);
  const visibleBars = bars.slice(safeWindowStart, safeWindowStart + safeVisibleCount);
  const inspectedOffset =
    hoveredOffset == null ? visibleBars.length - 1 : clamp(hoveredOffset, 0, visibleBars.length - 1);
  const inspectedBar = visibleBars[inspectedOffset];
  const inspectedIndex = safeWindowStart + inspectedOffset;
  const previousBar = bars[inspectedIndex - 1] ?? inspectedBar;

  const width = 1120;
  const height = 500;
  const topPadding = 26;
  const rightPadding = 88;
  const bottomPadding = 116;
  const leftPadding = 28;
  const chartBottom = height - bottomPadding;
  const volumeBase = height - 38;

  const highs = visibleBars.map((bar) => bar.high);
  const lows = visibleBars.map((bar) => bar.low);
  const volumes = visibleBars.map((bar) => bar.volume);
  const minPrice = Math.min(...lows);
  const maxPrice = Math.max(...highs);
  const maxVolume = Math.max(...volumes, 1);
  const slotWidth = (width - leftPadding - rightPadding) / visibleBars.length;
  const candleWidth = Math.max(8, Math.min(slotWidth * 0.62, 22));
  const priceDelta = inspectedBar.close - previousBar.close;
  const priceDeltaPercent = previousBar.close === 0 ? 0 : (priceDelta / previousBar.close) * 100;
  const gridLabels = Array.from({ length: 5 }, (_, index) => maxPrice - ((maxPrice - minPrice) * index) / 4);
  const gradientId = `volume-gradient-${symbol.toLowerCase()}`;
  const shiftStep = Math.max(1, Math.floor(safeVisibleCount / 3));

  function handleZoomChange(nextVisibleCount: number) {
    const clampedVisibleCount = clamp(nextVisibleCount, minVisibleCount, bars.length);
    const currentWindowEnd = safeWindowStart + visibleBars.length;
    const nextWindowStart = clamp(currentWindowEnd - clampedVisibleCount, 0, Math.max(0, bars.length - clampedVisibleCount));
    setVisibleCount(clampedVisibleCount);
    setWindowStart(nextWindowStart);
    setHoveredOffset((currentHoveredOffset) => {
      if (currentHoveredOffset == null) {
        return null;
      }
      return clamp(currentHoveredOffset, 0, clampedVisibleCount - 1);
    });
  }

  function shiftWindow(delta: number) {
    setWindowStart((currentWindowStart) => clamp(currentWindowStart + delta, 0, maxWindowStart));
  }

  return (
    <div className="candle-shell">
      <div className="candle-topline">
        <div>
          <span className="metric-label">Market Structure</span>
          <strong>{symbol} candlestick view</strong>
        </div>
        <div className="price-badge">
          <span>{formatCurrency(inspectedBar.close, currencyCode)}</span>
          <strong className={priceDelta >= 0 ? "positive" : "negative"}>
            {priceDelta >= 0 ? "+" : ""}
            {priceDelta.toFixed(2)} ({priceDeltaPercent.toFixed(2)}%)
          </strong>
        </div>
      </div>

      <div className="candle-toolbar">
        <div className="candle-toolbar-group">
          <button
            className="chart-control-button"
            onClick={() => shiftWindow(-shiftStep)}
            type="button"
            disabled={safeWindowStart === 0}
          >
            Earlier
          </button>
          <button
            className="chart-control-button"
            onClick={() => shiftWindow(shiftStep)}
            type="button"
            disabled={safeWindowStart >= maxWindowStart}
          >
            Later
          </button>
        </div>

        <label className="candle-range-control">
          <span>Zoom</span>
          <input
            className="chart-range"
            type="range"
            min={minVisibleCount}
            max={bars.length}
            step={1}
            value={safeVisibleCount}
            onChange={(event) => handleZoomChange(Number(event.target.value))}
          />
          <strong>{safeVisibleCount} candles</strong>
        </label>

        {maxWindowStart > 0 ? (
          <label className="candle-range-control candle-range-control-wide">
            <span>Scroll</span>
            <input
              className="chart-range"
              type="range"
              min={0}
              max={maxWindowStart}
              step={1}
              value={safeWindowStart}
              onChange={(event) => setWindowStart(Number(event.target.value))}
            />
            <strong>
              {safeWindowStart + 1}-{safeWindowStart + visibleBars.length} / {bars.length}
            </strong>
          </label>
        ) : null}
      </div>

      <div className="candle-inspector">
        <div className="candle-inspector-card">
          <span className="metric-label">Time</span>
          <strong>{formatDateTime(inspectedBar.timestamp)}</strong>
        </div>
        <div className="candle-inspector-card">
          <span className="metric-label">Open</span>
          <strong>{formatCurrency(inspectedBar.open, currencyCode)}</strong>
        </div>
        <div className="candle-inspector-card">
          <span className="metric-label">High</span>
          <strong>{formatCurrency(inspectedBar.high, currencyCode)}</strong>
        </div>
        <div className="candle-inspector-card">
          <span className="metric-label">Low</span>
          <strong>{formatCurrency(inspectedBar.low, currencyCode)}</strong>
        </div>
        <div className="candle-inspector-card">
          <span className="metric-label">Close</span>
          <strong>{formatCurrency(inspectedBar.close, currencyCode)}</strong>
        </div>
        <div className="candle-inspector-card">
          <span className="metric-label">Volume</span>
          <strong>{inspectedBar.volume.toFixed(0)}</strong>
        </div>
      </div>

      <svg className="candle-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${symbol} candlestick chart`}>
        <defs>
          <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#ef4444" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#ef4444" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {gridLabels.map((label) => {
          const y = getY(label, minPrice, maxPrice, chartBottom, topPadding, 22);
          return (
            <g key={label}>
              <line
                x1={leftPadding}
                x2={width - rightPadding}
                y1={y}
                y2={y}
                stroke="#cbd5e1"
                strokeDasharray="4 6"
                strokeWidth="1"
              />
              <text x={width - rightPadding + 12} y={y + 4} className="candle-axis-label">
                {label.toFixed(2)}
              </text>
            </g>
          );
        })}

        {visibleBars.map((bar, index) => {
          const xCenter = leftPadding + slotWidth * index + slotWidth / 2;
          const isInspected = index === inspectedOffset;
          const highlightX = xCenter - slotWidth / 2;

          return (
            <g key={`${bar.timestamp}-${index}`}>
              {isInspected ? (
                <>
                  <rect
                    x={highlightX}
                    y={topPadding}
                    width={slotWidth}
                    height={chartBottom - topPadding}
                    fill="rgba(239, 68, 68, 0.08)"
                    rx="8"
                  />
                  <line
                    x1={xCenter}
                    x2={xCenter}
                    y1={topPadding}
                    y2={chartBottom}
                    stroke="#ef4444"
                    strokeDasharray="4 5"
                    strokeWidth="1.5"
                  />
                </>
              ) : null}
            </g>
          );
        })}

        {visibleBars.map((bar, index) => {
          const xCenter = leftPadding + slotWidth * index + slotWidth / 2;
          const highY = getY(bar.high, minPrice, maxPrice, chartBottom, topPadding, 22);
          const lowY = getY(bar.low, minPrice, maxPrice, chartBottom, topPadding, 22);
          const openY = getY(bar.open, minPrice, maxPrice, chartBottom, topPadding, 22);
          const closeY = getY(bar.close, minPrice, maxPrice, chartBottom, topPadding, 22);
          const bodyY = Math.min(openY, closeY);
          const bodyHeight = Math.max(Math.abs(closeY - openY), 2);
          const isUp = bar.close >= bar.open;
          const volumeHeight = (bar.volume / maxVolume) * 56;

          return (
            <g key={`${bar.timestamp}-${index}`}>
              <line
                x1={xCenter}
                x2={xCenter}
                y1={highY}
                y2={lowY}
                stroke={isUp ? "#10b981" : "#ef4444"}
                strokeWidth={index === inspectedOffset ? "2.6" : "2"}
                strokeLinecap="round"
              />
              <rect
                x={xCenter - candleWidth / 2}
                y={bodyY}
                width={candleWidth}
                height={bodyHeight}
                rx="3"
                fill={isUp ? "#10b981" : "#ef4444"}
                opacity={index === inspectedOffset ? 1 : 0.92}
              />
              <rect
                x={xCenter - candleWidth / 2}
                y={volumeBase - volumeHeight}
                width={candleWidth}
                height={volumeHeight}
                rx="2"
                fill={`url(#${gradientId})`}
              />
              {index % Math.max(Math.floor(visibleBars.length / 6), 1) === 0 ? (
                <text x={xCenter - 15} y={height - 14} className="candle-axis-label">
                  {bar.timestamp.slice(11, 16)}
                </text>
              ) : null}
              <rect
                x={xCenter - slotWidth / 2}
                y={topPadding}
                width={slotWidth}
                height={chartBottom - topPadding}
                fill="transparent"
                onMouseEnter={() => setHoveredOffset(index)}
              />
            </g>
          );
        })}
      </svg>

      <div className="candle-footer">
        <div className="candle-legend">
          <span className="legend-up">Bull candle</span>
          <span className="legend-down">Bear candle</span>
          <span>Hover a candle to inspect OHLC and volume</span>
        </div>
        <span className="metric-label">{sourceLabel ?? "historical bars"}</span>
      </div>
    </div>
  );
}

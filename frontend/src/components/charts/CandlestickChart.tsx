import type { MarketBar } from "../../types/marketData";
import { formatCurrency } from "../../utils/format";

type CandlestickChartProps = {
  bars: MarketBar[];
  symbol: string;
  sourceLabel?: string;
};

function getY(value: number, min: number, max: number, height: number, top: number, bottom: number) {
  const range = max - min || 1;
  return top + ((max - value) / range) * (height - top - bottom);
}

export function CandlestickChart({ bars, symbol, sourceLabel }: CandlestickChartProps) {
  if (bars.length === 0) {
    return <div className="empty-state">No candles available for {symbol}.</div>;
  }

  const width = 1120;
  const height = 520;
  const topPadding = 24;
  const rightPadding = 88;
  const bottomPadding = 132;
  const leftPadding = 24;
  const chartBottom = height - bottomPadding;
  const volumeBase = height - 44;

  const highs = bars.map((bar) => bar.high);
  const lows = bars.map((bar) => bar.low);
  const volumes = bars.map((bar) => bar.volume);
  const minPrice = Math.min(...lows);
  const maxPrice = Math.max(...highs);
  const maxVolume = Math.max(...volumes, 1);
  const slotWidth = (width - leftPadding - rightPadding) / bars.length;
  const candleWidth = Math.max(4, Math.min(slotWidth * 0.58, 14));
  const latestBar = bars[bars.length - 1];
  const previousClose = bars.length > 1 ? bars[bars.length - 2].close : latestBar.open;
  const priceDelta = latestBar.close - previousClose;
  const priceDeltaPercent = previousClose === 0 ? 0 : (priceDelta / previousClose) * 100;
  const gridLabels = Array.from({ length: 5 }, (_, index) => maxPrice - ((maxPrice - minPrice) * index) / 4);

  return (
    <div className="candle-shell">
      <div className="candle-topline">
        <div>
          <span className="metric-label">Market Structure</span>
          <strong>{symbol} candlestick view</strong>
        </div>
        <div className="price-badge">
          <span>{formatCurrency(latestBar.close)}</span>
          <strong className={priceDelta >= 0 ? "positive" : "negative"}>
            {priceDelta >= 0 ? "+" : ""}
            {priceDelta.toFixed(2)} ({priceDeltaPercent.toFixed(2)}%)
          </strong>
        </div>
      </div>

      <svg className="candle-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${symbol} candlestick chart`}>
        <defs>
          <linearGradient id="volume-gradient" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="rgba(118, 249, 181, 0.55)" />
            <stop offset="100%" stopColor="rgba(118, 249, 181, 0.02)" />
          </linearGradient>
        </defs>

        {gridLabels.map((label) => {
          const y = getY(label, minPrice, maxPrice, chartBottom, topPadding, 24);
          return (
            <g key={label}>
              <line
                x1={leftPadding}
                x2={width - rightPadding}
                y1={y}
                y2={y}
                stroke="rgba(161, 183, 208, 0.18)"
                strokeDasharray="5 7"
              />
              <text x={width - rightPadding + 12} y={y + 4} className="candle-axis-label">
                {label.toFixed(2)}
              </text>
            </g>
          );
        })}

        {bars.map((bar, index) => {
          const xCenter = leftPadding + slotWidth * index + slotWidth / 2;
          const highY = getY(bar.high, minPrice, maxPrice, chartBottom, topPadding, 24);
          const lowY = getY(bar.low, minPrice, maxPrice, chartBottom, topPadding, 24);
          const openY = getY(bar.open, minPrice, maxPrice, chartBottom, topPadding, 24);
          const closeY = getY(bar.close, minPrice, maxPrice, chartBottom, topPadding, 24);
          const bodyY = Math.min(openY, closeY);
          const bodyHeight = Math.max(Math.abs(closeY - openY), 2);
          const isUp = bar.close >= bar.open;
          const volumeHeight = (bar.volume / maxVolume) * 64;

          return (
            <g key={`${bar.timestamp}-${index}`}>
              <line
                x1={xCenter}
                x2={xCenter}
                y1={highY}
                y2={lowY}
                stroke={isUp ? "#76f9b5" : "#ff7f8c"}
                strokeWidth="2"
                strokeLinecap="round"
              />
              <rect
                x={xCenter - candleWidth / 2}
                y={bodyY}
                width={candleWidth}
                height={bodyHeight}
                rx="3"
                fill={isUp ? "#76f9b5" : "#ff7f8c"}
              />
              <rect
                x={xCenter - candleWidth / 2}
                y={volumeBase - volumeHeight}
                width={candleWidth}
                height={volumeHeight}
                rx="2"
                fill="url(#volume-gradient)"
              />
              {index % Math.max(Math.floor(bars.length / 6), 1) === 0 ? (
                <text x={xCenter - 16} y={height - 14} className="candle-axis-label">
                  {bar.timestamp.slice(11, 16)}
                </text>
              ) : null}
            </g>
          );
        })}
      </svg>

      <div className="candle-footer">
        <div className="candle-legend">
          <span className="legend-up">Bull candle</span>
          <span className="legend-down">Bear candle</span>
        </div>
        <span className="metric-label">{sourceLabel ?? "historical bars"}</span>
      </div>
    </div>
  );
}

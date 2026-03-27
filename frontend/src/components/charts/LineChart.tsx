import { formatDateTime } from "../../utils/format";

type LineChartProps = {
  data: Array<{ timestamp: string; value: number }>;
  stroke: string;
  formatValue?: (value: number) => string;
};

export function LineChart({ data, stroke, formatValue }: LineChartProps) {
  if (data.length === 0) {
    return <div className="empty-state">No chart data available.</div>;
  }

  const width = 620;
  const height = 260;
  const padding = 24;
  const values = data.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const gridLabels = Array.from({ length: 4 }, (_, index) => max - (range * index) / 3);

  const path = data
    .map((point, index) => {
      const x = padding + (index / Math.max(data.length - 1, 1)) * (width - padding * 2);
      const y = height - padding - ((point.value - min) / range) * (height - padding * 2);
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");

  const areaPath = `${path} L ${width - padding} ${height - padding} L ${padding} ${height - padding} Z`;
  const latest = data[data.length - 1];
  const gradientId = `line-gradient-${stroke.replace(/[^a-z0-9]/gi, "").toLowerCase()}-${data.length}`;

  return (
    <div className="chart-shell">
      <svg className="chart-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Line chart">
        <defs>
          <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={stroke} stopOpacity="0.28" />
            <stop offset="100%" stopColor={stroke} stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {gridLabels.map((label) => {
          const y = height - padding - ((label - min) / range) * (height - padding * 2);
          return (
            <line
              key={label}
              x1={padding}
              x2={width - padding}
              y1={y}
              y2={y}
              stroke="#e2e8f0"
              strokeDasharray="4 6"
            />
          );
        })}

        <path d={areaPath} fill={`url(#${gradientId})`} />
        <path d={path} fill="none" stroke={stroke} strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
      </svg>

      <div className="chart-meta">
        <span>{formatDateTime(latest.timestamp)}</span>
        <strong>{formatValue ? formatValue(latest.value) : latest.value.toFixed(2)}</strong>
      </div>
    </div>
  );
}

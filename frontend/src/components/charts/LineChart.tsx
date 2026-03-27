type LineChartProps = {
  data: Array<{ timestamp: string; value: number }>;
  stroke: string;
  formatValue?: (value: number) => string;
};

export function LineChart({ data, stroke, formatValue }: LineChartProps) {
  if (data.length === 0) {
    return <div className="empty-state">No chart data available.</div>;
  }

  const width = 480;
  const height = 220;
  const padding = 18;
  const values = data.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const path = data
    .map((point, index) => {
      const x = padding + (index / Math.max(data.length - 1, 1)) * (width - padding * 2);
      const y = height - padding - ((point.value - min) / range) * (height - padding * 2);
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");

  const latest = data[data.length - 1];

  return (
    <div className="chart-shell">
      <svg className="chart-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Line chart">
        <path d={path} fill="none" stroke={stroke} strokeWidth="3" strokeLinejoin="round" />
      </svg>
      <div className="chart-meta">
        <span>{latest.timestamp.slice(0, 16).replace("T", " ")}</span>
        <strong>{formatValue ? formatValue(latest.value) : latest.value.toFixed(2)}</strong>
      </div>
    </div>
  );
}


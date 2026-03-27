type BarChartProps = {
  data: Array<{ label: string; value: number }>;
};

export function BarChart({ data }: BarChartProps) {
  if (data.length === 0) {
    return <div className="empty-state">No distribution data available.</div>;
  }

  const max = Math.max(...data.map((item) => item.value), 1);

  return (
    <div className="bars">
      {data.map((item) => (
        <div className="bar-row" key={item.label}>
          <span>{item.label}</span>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(item.value / max) * 100}%` }} />
          </div>
          <strong>{item.value.toFixed(1)}%</strong>
        </div>
      ))}
    </div>
  );
}


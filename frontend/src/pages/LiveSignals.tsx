import { DataTable } from "../components/DataTable";
import type { DashboardSnapshot } from "../types/dashboard";

type LiveSignalsProps = {
  snapshot: DashboardSnapshot | null;
};

export function LiveSignals({ snapshot }: LiveSignalsProps) {
  return (
    <section className="panel page-panel">
      <div className="panel-header">
        <h3>Signal Tape</h3>
        <p>BUY / SELL / HOLD outputs derived from the latest model predictions on real market data.</p>
      </div>
      <DataTable
        columns={["Symbol", "Signal", "Confidence", "Reason", "Timestamp"]}
        rows={(snapshot?.latest_signals ?? []).map((signal) => [
          signal.symbol,
          <span className={`signal-pill ${signal.signal_type.toLowerCase()}`} key={`${signal.symbol}-${signal.timestamp}`}>
            {signal.signal_type}
          </span>,
          `${((signal.confidence ?? 0) * 100).toFixed(1)}%`,
          signal.reason ?? "-",
          signal.timestamp.slice(0, 16).replace("T", " "),
        ])}
      />
    </section>
  );
}

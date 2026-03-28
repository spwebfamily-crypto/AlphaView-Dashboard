import { DataTable } from "../components/DataTable";
import { PageIntro } from "../components/page/PageIntro";
import type { DashboardSnapshot } from "../types/dashboard";
import { formatDateTime } from "../utils/format";

type LiveSignalsProps = {
  snapshot: DashboardSnapshot | null;
};

export function LiveSignals({ snapshot }: LiveSignalsProps) {
  const signals = snapshot?.latest_signals ?? [];
  const buyCount = signals.filter((signal) => signal.signal_type === "BUY").length;
  const avgConfidence =
    signals.length > 0
      ? signals.reduce((total, signal) => total + (signal.confidence ?? 0), 0) / signals.length
      : 0;
  const leadSignal = [...signals].sort((left, right) => (right.confidence ?? 0) - (left.confidence ?? 0))[0] ?? null;

  return (
    <div className="dashboard-page">
      <PageIntro
        eyebrow="Signal Desk"
        title="Live signal tape"
        description="Use this page to scan current model bias, confidence concentration, and the strongest names before moving into execution simulation."
        stats={[
          {
            label: "Active entries",
            value: signals.length,
            note: "Signals currently visible in the latest tape",
            tone: "accent",
          },
          {
            label: "Buy bias",
            value: `${buyCount}/${signals.length || 0}`,
            note: "Share of names currently mapped as BUY",
            tone: buyCount > 0 ? "positive" : "neutral",
          },
          {
            label: "Avg confidence",
            value: `${(avgConfidence * 100).toFixed(1)}%`,
            note: "Mean score across visible signals",
            tone: avgConfidence >= 0.6 ? "positive" : "neutral",
          },
          {
            label: "Lead symbol",
            value: leadSignal?.symbol ?? "-",
            note: leadSignal ? `${leadSignal.signal_type} at ${formatDateTime(leadSignal.timestamp)}` : "No ranked leader",
            tone: leadSignal?.signal_type === "SELL" ? "negative" : "accent",
          },
        ]}
      />

      {signals.length > 0 ? (
        <section className="detail-card-grid">
          {(leadSignal ? [leadSignal, ...signals.filter((signal) => signal !== leadSignal)] : signals)
            .slice(0, 3)
            .map((signal) => (
              <article className="detail-card" key={`${signal.symbol}-${signal.timestamp}`}>
                <div className="detail-card-topline">
                  <span className="metric-label">Signal candidate</span>
                  <span className={`signal-pill ${signal.signal_type.toLowerCase()}`}>{signal.signal_type}</span>
                </div>
                <strong>{signal.symbol}</strong>
                <p>{signal.reason ?? "Research this setup before promoting it to execution simulation."}</p>
                <div className="detail-card-meta">
                  <span>{((signal.confidence ?? 0) * 100).toFixed(1)}% confidence</span>
                  <span>{formatDateTime(signal.timestamp)}</span>
                </div>
              </article>
            ))}
        </section>
      ) : null}

      <section className="panel page-panel">
        <div className="panel-header">
          <div>
            <h3>Signal tape</h3>
            <p>BUY / SELL / HOLD outputs derived from the latest model predictions on real market data.</p>
          </div>
        </div>
        <DataTable
          columns={["Symbol", "Signal", "Confidence", "Reason", "Timestamp"]}
          rows={(snapshot?.latest_signals ?? []).map((signal) => [
            <span className="table-symbol" key={`${signal.symbol}-symbol`}>
              {signal.symbol}
            </span>,
            <span className={`signal-pill ${signal.signal_type.toLowerCase()}`} key={`${signal.symbol}-${signal.timestamp}`}>
              {signal.signal_type}
            </span>,
            `${((signal.confidence ?? 0) * 100).toFixed(1)}%`,
            signal.reason ?? "-",
            formatDateTime(signal.timestamp),
          ])}
          caption="Current signal queue"
          footnote="Signals are research outputs, not guaranteed outcomes. Validate context in Overview before simulating an order."
        />
      </section>
    </div>
  );
}

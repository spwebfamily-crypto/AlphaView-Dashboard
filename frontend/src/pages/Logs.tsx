import { DataTable } from "../components/DataTable";
import { PageIntro } from "../components/page/PageIntro";
import type { DashboardSnapshot } from "../types/dashboard";
import { formatDateTime } from "../utils/format";

type LogsProps = {
  snapshot: DashboardSnapshot | null;
};

export function Logs({ snapshot }: LogsProps) {
  const logs = snapshot?.logs ?? [];
  const recentLogs = [...logs].sort((left, right) => right.timestamp.localeCompare(left.timestamp));
  const errorCount = logs.filter((entry) => /(error|critical|fatal)/i.test(entry.level)).length;
  const warningCount = logs.filter((entry) => /warn/i.test(entry.level)).length;
  const infoCount = logs.filter((entry) => /info/i.test(entry.level)).length;
  const latestLog = recentLogs[0] ?? null;
  const latestLogTone = latestLog
    ? (getLogTone(latestLog.level).replace("tone-", "") as "neutral" | "positive" | "negative" | "accent" | "warning")
    : "neutral";

  return (
    <div className="dashboard-page">
      <PageIntro
        eyebrow="System Events"
        title="Operational event trail"
        description="Inspect ingestion, training, backtest, and broker activity with a clearer severity hierarchy and faster access to the latest issues."
        stats={[
          {
            label: "Events stored",
            value: logs.length,
            note: "Structured service events currently available in the dashboard snapshot",
            tone: "accent",
          },
          {
            label: "Errors",
            value: errorCount,
            note: "High-severity events that likely require operator attention",
            tone: errorCount > 0 ? "negative" : "neutral",
          },
          {
            label: "Warnings",
            value: warningCount,
            note: `${infoCount} informational events alongside warning activity`,
            tone: warningCount > 0 ? "warning" : "neutral",
          },
          {
            label: "Latest event",
            value: latestLog ? formatDateTime(latestLog.timestamp) : "-",
            note: latestLog ? latestLog.level : "No events stored",
            tone: latestLogTone,
          },
        ]}
      />

      {recentLogs.length > 0 ? (
        <section className="detail-card-grid">
          {recentLogs.slice(0, 3).map((entry, index) => (
            <article className="detail-card" key={`${entry.timestamp}-${index}`}>
              <div className="detail-card-topline">
                <span className="metric-label">{index === 0 ? "Most recent event" : "Event detail"}</span>
                <span className={`tone-pill ${getLogTone(entry.level)}`}>{entry.level}</span>
              </div>
              <strong>{formatDateTime(entry.timestamp)}</strong>
              <p>{entry.message}</p>
              <div className="detail-card-meta">
                <span>Structured log</span>
                <span>{entry.level}</span>
              </div>
            </article>
          ))}
        </section>
      ) : null}

      <section className="panel page-panel">
        <div className="panel-header">
          <div>
            <h3>System logs</h3>
            <p>Structured events emitted by ingestion, training, backtesting, and broker services.</p>
          </div>
        </div>
        <DataTable
          columns={["Timestamp", "Level", "Message"]}
          rows={recentLogs.map((entry) => [
            formatDateTime(entry.timestamp),
            <span className={`tone-pill ${getLogTone(entry.level)}`} key={`${entry.timestamp}-level`}>
              {entry.level}
            </span>,
            entry.message,
          ])}
          caption="Recent service event log"
          footnote="Structured logs help diagnose ingestion, model, and execution issues; review errors before assuming a data or strategy failure."
        />
      </section>
    </div>
  );
}

function getLogTone(level: string) {
  if (/(error|critical|fatal)/i.test(level)) {
    return "tone-negative";
  }
  if (/warn/i.test(level)) {
    return "tone-warning";
  }
  if (/info|debug/i.test(level)) {
    return "tone-neutral";
  }
  return "tone-accent";
}

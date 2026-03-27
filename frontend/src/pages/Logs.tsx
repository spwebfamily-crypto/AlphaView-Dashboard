import { DataTable } from "../components/DataTable";
import type { DashboardSnapshot } from "../types/dashboard";
import { formatDateTime } from "../utils/format";

type LogsProps = {
  snapshot: DashboardSnapshot | null;
};

export function Logs({ snapshot }: LogsProps) {
  return (
    <section className="panel page-panel">
      <div className="panel-header">
        <h3>System Logs</h3>
        <p>Structured events emitted by ingestion, training, backtesting, and broker services.</p>
      </div>
      <DataTable
        columns={["Timestamp", "Level", "Message"]}
        rows={(snapshot?.logs ?? []).map((entry) => [
          formatDateTime(entry.timestamp),
          entry.level,
          entry.message,
        ])}
      />
    </section>
  );
}


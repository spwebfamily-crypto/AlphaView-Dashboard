import { DataTable } from "../components/DataTable";
import type { DashboardSnapshot } from "../types/dashboard";
import { formatDateTime } from "../utils/format";

type LogsProps = {
  snapshot: DashboardSnapshot | null;
};

export function Logs({ snapshot }: LogsProps) {
  return (
    <div className="dashboard-page">
      <section className="panel page-panel">
        <div className="panel-header">
          <div>
            <h3>System logs</h3>
            <p>Structured events emitted by ingestion, training, backtesting, and broker services.</p>
          </div>
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
    </div>
  );
}

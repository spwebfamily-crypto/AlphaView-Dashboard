import { DataTable } from "../components/DataTable";
import { BarChart } from "../components/charts/BarChart";
import { LineChart } from "../components/charts/LineChart";
import type { DashboardSnapshot } from "../types/dashboard";
import { formatPercent } from "../utils/format";

type BacktestsProps = {
  snapshot: DashboardSnapshot | null;
};

export function Backtests({ snapshot }: BacktestsProps) {
  return (
    <div className="dashboard-page">
      <div className="dashboard-grid dashboard-grid-secondary">
        <section className="panel">
          <div className="panel-header">
            <div>
              <h3>Backtest equity</h3>
              <p>Latest stored equity path from the most recent research runs.</p>
            </div>
          </div>
          <LineChart
            data={(snapshot?.equity_curve ?? []).map((point) => ({
              timestamp: point.timestamp,
              value: point.equity ?? 0,
            }))}
            stroke="#2563eb"
          />
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h3>Outcome distribution</h3>
              <p>Quick distribution read for the current stored strategy outcomes.</p>
            </div>
          </div>
          <BarChart data={snapshot?.win_loss_distribution ?? []} />
        </section>
      </div>

      <section className="panel page-panel">
        <div className="panel-header">
          <div>
            <h3>Backtest runs</h3>
            <p>Total return, Sharpe, and trade count snapshots from the research archive.</p>
          </div>
        </div>
        <DataTable
          columns={["ID", "Name", "Status", "Total Return", "Sharpe", "Trades"]}
          rows={(snapshot?.backtests ?? []).map((run) => [
            run.id,
            run.name,
            run.status,
            formatPercent(run.total_return * 100),
            run.sharpe.toFixed(2),
            run.trade_count,
          ])}
        />
      </section>
    </div>
  );
}

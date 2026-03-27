import { DataTable } from "../components/DataTable";
import { LineChart } from "../components/charts/LineChart";
import type { DashboardSnapshot } from "../types/dashboard";
import { formatPercent } from "../utils/format";

type BacktestsProps = {
  snapshot: DashboardSnapshot | null;
};

export function Backtests({ snapshot }: BacktestsProps) {
  return (
    <div className="page-grid compact">
      <section className="panel chart-panel">
        <div className="panel-header">
          <h3>Backtest Equity</h3>
          <p>Latest stored run</p>
        </div>
        <LineChart
          data={(snapshot?.equity_curve ?? []).map((point) => ({
            timestamp: point.timestamp,
            value: point.equity ?? 0,
          }))}
          stroke="#76f9b5"
        />
      </section>

      <section className="panel page-panel">
        <div className="panel-header">
          <h3>Backtest Runs</h3>
          <p>Total return, Sharpe, and trade count snapshots.</p>
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

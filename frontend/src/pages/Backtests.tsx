import { DataTable } from "../components/DataTable";
import { BarChart } from "../components/charts/BarChart";
import { LineChart } from "../components/charts/LineChart";
import { PageIntro } from "../components/page/PageIntro";
import type { DashboardSnapshot } from "../types/dashboard";
import { formatPercent } from "../utils/format";

type BacktestsProps = {
  snapshot: DashboardSnapshot | null;
};

export function Backtests({ snapshot }: BacktestsProps) {
  const runs = snapshot?.backtests ?? [];
  const leadRun = [...runs].sort((left, right) => right.sharpe + right.total_return - (left.sharpe + left.total_return))[0] ?? null;
  const averageSharpe = runs.length > 0 ? runs.reduce((total, run) => total + run.sharpe, 0) / runs.length : 0;
  const positiveRuns = runs.filter((run) => run.total_return > 0).length;
  const totalTrades = runs.reduce((total, run) => total + run.trade_count, 0);

  return (
    <div className="dashboard-page">
      <PageIntro
        eyebrow="Research Archive"
        title="Backtest command center"
        description="Compare historical runs, equity behavior, and outcome quality before turning a strategy idea into a paper-trading workflow."
        stats={[
          {
            label: "Stored runs",
            value: runs.length,
            note: `${positiveRuns}/${runs.length || 0} runs currently positive on total return`,
            tone: "accent",
          },
          {
            label: "Average Sharpe",
            value: averageSharpe.toFixed(2),
            note: "Mean risk-adjusted score across the current archive",
            tone: averageSharpe >= 1 ? "positive" : "neutral",
          },
          {
            label: "Trade sample",
            value: totalTrades,
            note: "Total executed trades across stored backtest runs",
            tone: "neutral",
          },
          {
            label: "Lead strategy",
            value: leadRun?.name ?? "-",
            note: leadRun ? `${formatPercent(leadRun.total_return * 100)} total return` : "No archived run available",
            tone: "accent",
          },
        ]}
      />

      {runs.length > 0 ? (
        <section className="detail-card-grid">
          {[...runs]
            .sort((left, right) => right.sharpe + right.total_return - (left.sharpe + left.total_return))
            .slice(0, 3)
            .map((run) => (
              <article className="detail-card" key={run.id}>
                <div className="detail-card-topline">
                  <span className="metric-label">Research run</span>
                  <span className={`tone-pill ${getBacktestTone(run.status, run.total_return)}`}>{run.status}</span>
                </div>
                <strong>{run.name}</strong>
                <p>Sharpe {run.sharpe.toFixed(2)} across {run.trade_count} trades in the current research archive.</p>
                <div className="detail-card-meta">
                  <span className={run.total_return >= 0 ? "table-number is-positive" : "table-number is-negative"}>
                    {formatPercent(run.total_return * 100)}
                  </span>
                  <span>{run.trade_count} trades</span>
                </div>
              </article>
            ))}
        </section>
      ) : null}

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
            stroke="#dc2626"
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
          rows={runs.map((run) => [
            run.id,
            <span className="table-symbol" key={`backtest-name-${run.id}`}>
              {run.name}
            </span>,
            <span className={`tone-pill ${getBacktestTone(run.status, run.total_return)}`} key={`backtest-status-${run.id}`}>
              {run.status}
            </span>,
            <span className={run.total_return >= 0 ? "table-number is-positive" : "table-number is-negative"} key={`backtest-return-${run.id}`}>
              {formatPercent(run.total_return * 100)}
            </span>,
            <span className="table-number" key={`backtest-sharpe-${run.id}`}>
              {run.sharpe.toFixed(2)}
            </span>,
            run.trade_count,
          ])}
          caption="Stored research runs"
          footnote="Backtests summarize historical simulation only. They are useful for research ranking, not as proof of future returns."
        />
      </section>
    </div>
  );
}

function getBacktestTone(status: string, totalReturn: number) {
  const normalizedStatus = status.toLowerCase();
  if (normalizedStatus.includes("complete") || normalizedStatus.includes("finished")) {
    return totalReturn >= 0 ? "tone-positive" : "tone-negative";
  }
  if (normalizedStatus.includes("run") || normalizedStatus.includes("queue") || normalizedStatus.includes("pending")) {
    return "tone-warning";
  }
  if (normalizedStatus.includes("fail") || normalizedStatus.includes("error")) {
    return "tone-negative";
  }
  return "tone-accent";
}

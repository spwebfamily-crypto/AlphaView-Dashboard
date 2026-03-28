import { DataTable } from "../components/DataTable";
import { PageIntro } from "../components/page/PageIntro";
import type { Execution, Order } from "../types/broker";
import { formatCurrency, formatDateTime } from "../utils/format";

type TradesProps = {
  orders: Order[];
  executions: Execution[];
};

export function Trades({ orders, executions }: TradesProps) {
  const buyOrders = orders.filter((order) => order.side.toUpperCase() === "BUY").length;
  const sellOrders = orders.filter((order) => order.side.toUpperCase() === "SELL").length;
  const totalExecutedNotional = executions.reduce((total, execution) => total + execution.price * execution.quantity, 0);
  const totalFees = executions.reduce((total, execution) => total + (execution.fees ?? 0), 0);
  const latestOrder = [...orders].sort((left, right) => (right.submitted_at ?? "").localeCompare(left.submitted_at ?? ""))[0] ?? null;
  const latestExecution = [...executions].sort((left, right) => right.executed_at.localeCompare(left.executed_at))[0] ?? null;

  return (
    <div className="dashboard-page">
      <PageIntro
        eyebrow="Execution Desk"
        title="Order and fill monitor"
        description="Review queue health, fill cadence, and transaction costs across the simulated execution layer before changing routing assumptions."
        stats={[
          {
            label: "Orders logged",
            value: orders.length,
            note: `${buyOrders} buy / ${sellOrders} sell instructions in the current archive`,
            tone: "accent",
          },
          {
            label: "Fills booked",
            value: executions.length,
            note: latestExecution ? `Last fill ${formatDateTime(latestExecution.executed_at)}` : "No simulated fills yet",
            tone: executions.length > 0 ? "positive" : "neutral",
          },
          {
            label: "Executed notional",
            value: formatCurrency(totalExecutedNotional),
            note: "Aggregate notional across stored simulated fills",
            tone: "neutral",
          },
          {
            label: "Fees tracked",
            value: formatCurrency(totalFees),
            note: "Total modeled transaction costs from stored executions",
            tone: totalFees > 0 ? "negative" : "neutral",
          },
        ]}
      />

      <section className="detail-card-grid">
        <article className="detail-card">
          <div className="detail-card-topline">
            <span className="metric-label">Flow balance</span>
            <span className="tone-pill tone-accent">Order mix</span>
          </div>
          <strong>{buyOrders >= sellOrders ? "Buy-side pressure" : "Sell-side pressure"}</strong>
          <p>The current paper order tape is tilted toward the side with the highest count of instructions.</p>
          <div className="detail-card-meta">
            <span>{buyOrders} buy orders</span>
            <span>{sellOrders} sell orders</span>
          </div>
        </article>

        <article className="detail-card">
          <div className="detail-card-topline">
            <span className="metric-label">Latest order</span>
            <span className={`tone-pill ${getOrderTone(latestOrder?.status ?? "")}`}>{latestOrder?.status ?? "No order"}</span>
          </div>
          <strong>{latestOrder?.symbol ?? "-"}</strong>
          <p>
            {latestOrder
              ? `${latestOrder.side} ${latestOrder.quantity.toFixed(2)} shares via ${latestOrder.order_type}.`
              : "No stored order has been submitted yet."}
          </p>
          <div className="detail-card-meta">
            <span>{latestOrder ? `Order #${latestOrder.id}` : "Waiting for activity"}</span>
            <span>{latestOrder ? formatDateTime(latestOrder.submitted_at) : "-"}</span>
          </div>
        </article>

        <article className="detail-card">
          <div className="detail-card-topline">
            <span className="metric-label">Latest fill</span>
            <span className="tone-pill tone-positive">{latestExecution ? "Booked" : "Pending"}</span>
          </div>
          <strong>{latestExecution ? formatCurrency(latestExecution.price) : "-"}</strong>
          <p>
            {latestExecution
              ? `${latestExecution.quantity.toFixed(2)} shares executed with ${formatCurrency(latestExecution.fees)} fees.`
              : "Executions will appear here after the simulator creates fills from stored market prices."}
          </p>
          <div className="detail-card-meta">
            <span>{latestExecution ? `Order #${latestExecution.order_id}` : "No fills stored"}</span>
            <span>{latestExecution ? formatDateTime(latestExecution.executed_at) : "-"}</span>
          </div>
        </article>
      </section>

      <div className="dashboard-grid dashboard-grid-secondary">
        <section className="panel page-panel">
          <div className="panel-header">
            <div>
              <h3>Orders</h3>
              <p>Simulation order flow built on top of the latest stored market prices.</p>
            </div>
          </div>
          <DataTable
            columns={["ID", "Symbol", "Side", "Type", "Qty", "Status", "Submitted"]}
            rows={orders.map((order) => [
              order.id,
              <span className="table-symbol" key={`order-symbol-${order.id}`}>
                {order.symbol}
              </span>,
              <span className={`tone-pill ${order.side.toUpperCase() === "BUY" ? "tone-positive" : "tone-negative"}`} key={`order-side-${order.id}`}>
                {order.side}
              </span>,
              order.order_type,
              order.quantity.toFixed(2),
              <span className={`tone-pill ${getOrderTone(order.status)}`} key={`order-status-${order.id}`}>
                {order.status}
              </span>,
              formatDateTime(order.submitted_at),
            ])}
            caption="Order archive"
            footnote="All orders shown here belong to the paper execution layer and are not routed to a live broker by default."
          />
        </section>

        <section className="panel page-panel">
          <div className="panel-header">
            <div>
              <h3>Executions</h3>
              <p>Simulated fills derived from real market bars with slippage and fee assumptions.</p>
            </div>
          </div>
          <DataTable
            columns={["Exec ID", "Order ID", "Price", "Qty", "Fees", "Executed At"]}
            rows={executions.map((execution) => [
              execution.id,
              execution.order_id,
              <span className="table-number" key={`exec-price-${execution.id}`}>
                {formatCurrency(execution.price)}
              </span>,
              execution.quantity.toFixed(2),
              <span className="table-number is-negative" key={`exec-fees-${execution.id}`}>
                {formatCurrency(execution.fees)}
              </span>,
              formatDateTime(execution.executed_at),
            ])}
            caption="Execution archive"
            footnote="Execution records are generated from the simulator with modeled slippage and fees on top of stored market data."
          />
        </section>
      </div>
    </div>
  );
}

function getOrderTone(status: string) {
  const normalizedStatus = status.toLowerCase();
  if (normalizedStatus.includes("fill") || normalizedStatus.includes("complete")) {
    return "tone-positive";
  }
  if (normalizedStatus.includes("cancel") || normalizedStatus.includes("reject")) {
    return "tone-negative";
  }
  if (normalizedStatus.includes("pending") || normalizedStatus.includes("submit")) {
    return "tone-warning";
  }
  return "tone-accent";
}

import { DataTable } from "../components/DataTable";
import type { Execution, Order } from "../types/broker";
import { formatCurrency, formatDateTime } from "../utils/format";

type TradesProps = {
  orders: Order[];
  executions: Execution[];
};

export function Trades({ orders, executions }: TradesProps) {
  return (
    <div className="dashboard-page">
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
              order.symbol,
              order.side,
              order.order_type,
              order.quantity.toFixed(2),
              order.status,
              formatDateTime(order.submitted_at),
            ])}
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
              formatCurrency(execution.price),
              execution.quantity.toFixed(2),
              formatCurrency(execution.fees),
              formatDateTime(execution.executed_at),
            ])}
          />
        </section>
      </div>
    </div>
  );
}

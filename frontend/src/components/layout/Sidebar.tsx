export type PageKey =
  | "overview"
  | "signals"
  | "positions"
  | "trades"
  | "backtests"
  | "models"
  | "logs"
  | "account"
  | "billing"
  | "settings";

type SidebarProps = {
  activePage: PageKey;
  onSelect: (page: PageKey) => void;
};

const navItems: Array<{ key: PageKey; label: string; hint: string; marker: string }> = [
  { key: "overview", label: "Overview", hint: "Market structure and ranked ideas", marker: "OV" },
  { key: "signals", label: "Signals", hint: "Latest BUY / SELL / HOLD tape", marker: "SG" },
  { key: "positions", label: "Positions", hint: "Simulated inventory and PnL", marker: "PS" },
  { key: "trades", label: "Trades", hint: "Orders, fills, fees, slippage", marker: "TR" },
  { key: "backtests", label: "Backtests", hint: "Equity curve and run archive", marker: "BT" },
  { key: "models", label: "Models", hint: "Model registry and diagnostics", marker: "ML" },
  { key: "logs", label: "Logs", hint: "Recent system events", marker: "LG" },
  { key: "account", label: "Account", hint: "Login, payouts, Stripe Connect", marker: "AC" },
  { key: "billing", label: "Billing", hint: "Checkout, subscriptions, customer portal", marker: "BL" },
  { key: "settings", label: "Settings", hint: "Runtime and provider status", marker: "ST" },
];

export function Sidebar({ activePage, onSelect }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-logo">A</div>
        <div>
          <span className="sidebar-label">AlphaView OS</span>
          <h2>Admin Desk</h2>
        </div>
      </div>

      <p className="sidebar-copy">
        Notus-style control surface for market research, signals, and simulation oriented to European equities.
      </p>

      <nav className="sidebar-nav" aria-label="Primary">
        {navItems.map((item) => (
          <button
            key={item.key}
            className={`nav-item ${activePage === item.key ? "active" : ""}`}
            onClick={() => onSelect(item.key)}
            type="button"
          >
            <span className="nav-icon">{item.marker}</span>
            <span className="nav-copy">
              <strong>{item.label}</strong>
              <small>{item.hint}</small>
            </span>
          </button>
        ))}
      </nav>

      <div className="sidebar-note">
        <span className="eyebrow">Environment</span>
        <p>
          Simulation only. Historical and status data are real, but order routing stays local and no broker claims are
          made by the interface.
        </p>
      </div>
    </aside>
  );
}

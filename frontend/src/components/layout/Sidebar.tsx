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

const navSections: Array<{ label: string; items: typeof navItems }> = [
  {
    label: "Market stack",
    items: navItems.filter((item) =>
      ["overview", "signals", "positions", "trades", "backtests", "models"].includes(item.key),
    ),
  },
  {
    label: "Platform stack",
    items: navItems.filter((item) => ["logs", "account", "billing", "settings"].includes(item.key)),
  },
];

export function Sidebar({ activePage, onSelect }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand-panel">
        <div className="sidebar-brand">
          <div className="sidebar-logo-wrap">
            <div className="sidebar-logo">AV</div>
            <span className="sidebar-logo-beam" />
          </div>
          <div className="sidebar-brand-copy">
            <span className="sidebar-label">AlphaView Command</span>
            <h2>Operator Grid</h2>
            <p>Research, paper execution, and commercial controls in one European equities surface.</p>
          </div>
        </div>

        <div className="sidebar-status-card">
          <span className="metric-label">Operating posture</span>
          <strong>PAPER by default</strong>
          <small>Real market inputs, local execution, and no live-return claims in the interface.</small>
        </div>
      </div>

      <div className="sidebar-sections">
        {navSections.map((section) => (
          <div className="nav-section" key={section.label}>
            <span className="sidebar-section-label">{section.label}</span>
            <nav className="sidebar-nav" aria-label={section.label}>
              {section.items.map((item) => (
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
          </div>
        ))}
      </div>

      <div className="sidebar-note">
        <span className="eyebrow">Protocol</span>
        <p>
          Treat the dashboard as a research and paper-trading platform. Billing and payout controls are real, but
          market claims and execution remain bounded by provider and simulation rules.
        </p>
      </div>
    </aside>
  );
}

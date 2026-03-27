export type PageKey = "overview" | "signals" | "positions" | "trades" | "backtests" | "models" | "logs" | "settings";

type SidebarProps = {
  activePage: PageKey;
  onSelect: (page: PageKey) => void;
};

const navItems: Array<{ key: PageKey; label: string; hint: string }> = [
  { key: "overview", label: "Overview", hint: "Candles, ranked ideas, and market context" },
  { key: "signals", label: "Signals", hint: "Fresh BUY / SELL / HOLD outputs" },
  { key: "positions", label: "Positions", hint: "Simulated inventory from the execution engine" },
  { key: "trades", label: "Trades", hint: "Orders, fills, slippage, and fees" },
  { key: "backtests", label: "Backtests", hint: "Research performance and equity curves" },
  { key: "models", label: "Models", hint: "Baseline model registry and diagnostics" },
  { key: "logs", label: "Logs", hint: "Recent system events and warnings" },
  { key: "settings", label: "Settings", hint: "Runtime defaults and simulation status" },
];

export function Sidebar({ activePage, onSelect }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="eyebrow">Market Research Terminal</span>
        <h2>AlphaView</h2>
        <p className="sidebar-copy">
          Real market candles, buy-side research, and simulated execution kept in one operating view.
        </p>
      </div>

      <nav className="sidebar-nav" aria-label="Primary">
        {navItems.map((item) => (
          <button
            key={item.key}
            className={`nav-item ${activePage === item.key ? "active" : ""}`}
            onClick={() => onSelect(item.key)}
            type="button"
          >
            <span>{item.label}</span>
            <small>{item.hint}</small>
          </button>
        ))}
      </nav>

      <div className="sidebar-note">
        <span className="eyebrow">Operating Mode</span>
        <p className="sidebar-copy">
          The dashboard is optimized for research and simulation over real historical data, not external broker routing.
        </p>
      </div>
    </aside>
  );
}

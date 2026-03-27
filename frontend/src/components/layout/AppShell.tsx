import type { ReactNode } from "react";

import type { PageKey } from "./Sidebar";
import { Sidebar } from "./Sidebar";
import { ModeBadge } from "../status/ModeBadge";

type AppShellProps = {
  children: ReactNode;
  mode: string;
  activePage: PageKey;
  onPageChange: (page: PageKey) => void;
  apiStatus: string;
};

export function AppShell({ children, mode, activePage, onPageChange, apiStatus }: AppShellProps) {
  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} onSelect={onPageChange} />

      <div className="workspace">
        <header className="topbar">
          <div className="topbar-copy">
            <p className="eyebrow">US EQUITIES RESEARCH TERMINAL</p>
            <h1>AlphaView Market Board</h1>
            <p className="topbar-subtitle">
              Candles first, buy research second, simulation only after the thesis survives scrutiny.
            </p>
          </div>
          <div className="topbar-actions">
            <span className={`status-indicator ${apiStatus === "online" ? "online" : "offline"}`}>
              {apiStatus === "online" ? "API online" : "API degraded"}
            </span>
            <ModeBadge mode={mode} />
          </div>
        </header>

        <main className="content-grid">{children}</main>
      </div>
    </div>
  );
}

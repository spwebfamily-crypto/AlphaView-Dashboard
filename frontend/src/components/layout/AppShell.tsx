import type { ReactNode } from "react";

import { formatDateTime } from "../../utils/format";
import { ModeBadge } from "../status/ModeBadge";
import type { PageKey } from "./Sidebar";
import { Sidebar } from "./Sidebar";

export type ShellStatCard = {
  label: string;
  value: string;
  meta: string;
  tone: "blue" | "emerald" | "amber" | "slate";
};

type AppShellProps = {
  children: ReactNode;
  mode: string;
  activePage: PageKey;
  onPageChange: (page: PageKey) => void;
  apiStatus: string;
  eyebrow: string;
  title: string;
  description: string;
  generatedAt?: string | null;
  headerCards: ShellStatCard[];
};

function getInitials(label: string) {
  return label
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export function AppShell({
  children,
  mode,
  activePage,
  onPageChange,
  apiStatus,
  eyebrow,
  title,
  description,
  generatedAt,
  headerCards,
}: AppShellProps) {
  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} onSelect={onPageChange} />

      <div className="workspace">
        <header className="topbar">
          <div className="topbar-copy">
            <span className="eyebrow">{eyebrow}</span>
            <h1>{title}</h1>
            <p>{description}</p>
          </div>

          <div className="topbar-actions">
            <div className="topbar-status">
              <span className={`status-indicator ${apiStatus === "online" ? "online" : "offline"}`}>
                {apiStatus === "online" ? "API online" : "API degraded"}
              </span>
              <small>{formatDateTime(generatedAt)}</small>
            </div>
            <ModeBadge mode={mode} />
          </div>
        </header>

        <section className="header-band">
          <div className="header-band-copy">
            <span className="eyebrow">Simulation Layer</span>
            <h2>Real market data in a cleaner admin control room.</h2>
            <p>
              Review market structure, model output, backtests, and simulated execution from one shell without the old
              dark research-terminal look.
            </p>
          </div>

          <div className="header-band-meta">
            <div className="band-field">
              <span>Module</span>
              <strong>{title}</strong>
            </div>
            <div className="band-field">
              <span>Mode</span>
              <strong>{mode.toUpperCase() === "PAPER" ? "SIMULATION" : mode.toUpperCase()}</strong>
            </div>
            <div className="band-field">
              <span>Snapshot</span>
              <strong>{generatedAt ? formatDateTime(generatedAt) : "Waiting for data"}</strong>
            </div>
          </div>
        </section>

        <section className="header-stat-row">
          {headerCards.map((card) => (
            <article className={`header-stat-card tone-${card.tone}`} key={card.label}>
              <span className={`stat-card-icon tone-${card.tone}`}>{getInitials(card.label)}</span>
              <div className="stat-card-copy">
                <span>{card.label}</span>
                <strong>{card.value}</strong>
                <small>{card.meta}</small>
              </div>
            </article>
          ))}
        </section>

        <main className="content-grid">{children}</main>
      </div>
    </div>
  );
}

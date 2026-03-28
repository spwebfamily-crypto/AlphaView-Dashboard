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
  userLabel: string;
  onSignOut: () => void;
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
  userLabel,
  onSignOut,
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
            <div className="topbar-system">
              <div className="topbar-status-card">
                <span className={`status-indicator ${apiStatus === "online" ? "online" : "offline"}`}>
                  {apiStatus === "online" ? "API online" : "API degraded"}
                </span>
                <small>{generatedAt ? `Snapshot ${formatDateTime(generatedAt)}` : "Waiting for snapshot"}</small>
              </div>
              <div className="topbar-mode-card">
                <span className="metric-label">Execution</span>
                <ModeBadge mode={mode} />
              </div>
            </div>

            <div className="account-chip">
              <span className="account-avatar">{getInitials(userLabel)}</span>
              <div className="account-copy">
                <strong>{userLabel}</strong>
                <small>Authenticated operator</small>
              </div>
              <button className="ghost-button" onClick={onSignOut} type="button">
                Sign out
              </button>
            </div>
          </div>
        </header>

        <section className="header-band">
          <div className="header-band-copy">
            <span className="eyebrow">Control Surface</span>
            <h2>Research, validation, and paper execution in one operating layer.</h2>
            <p>
              Keep the market tape, model evidence, runtime state, and commercial flows aligned in a single dashboard
              built for operator clarity.
            </p>
            <div className="hero-chip-row">
              <span className="hero-chip">Market intelligence</span>
              <span className="hero-chip">Paper execution</span>
              <span className="hero-chip">Commercial controls</span>
            </div>
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

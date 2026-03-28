import { useEffect, useState } from "react";

import {
  fetchBrokerStatus,
  fetchCurrentUser,
  fetchDashboardSnapshot,
  fetchExecutions,
  fetchHealth,
  fetchOrders,
  fetchRuntimeSettings,
  logoutAccount,
  refreshCurrentSession,
  seedDemoData,
} from "./api/client";
import { AuthScreen } from "./components/auth/AuthScreen";
import { AppShell, type ShellStatCard } from "./components/layout/AppShell";
import type { PageKey } from "./components/layout/Sidebar";
import { Account } from "./pages/Account";
import { Backtests } from "./pages/Backtests";
import { Billing } from "./pages/Billing";
import { LiveSignals } from "./pages/LiveSignals";
import { Logs } from "./pages/Logs";
import { Models } from "./pages/Models";
import { Overview } from "./pages/OverviewNew";
import "./styles/overview.css";
import { Positions } from "./pages/Positions";
import { Settings } from "./pages/Settings";
import { Trades } from "./pages/Trades";
import type { AuthSession, AuthUser } from "./types/auth";
import type { BrokerStatus, Execution, Order } from "./types/broker";
import type { DashboardBacktest, DashboardSnapshot, SummaryCard } from "./types/dashboard";
import type { HealthResponse } from "./types/health";
import type { RuntimeSettings } from "./types/runtime";
import { formatCurrency, formatPercent } from "./utils/format";

const pageCopy: Record<PageKey, { eyebrow: string; title: string; description: string }> = {
  overview: {
    eyebrow: "Command overview",
    title: "Research command center",
    description: "Work the market tape, ranked setups, and chart context from one decisive operator surface.",
  },
  signals: {
    eyebrow: "Signal grid",
    title: "Live signal command",
    description: "Inspect conviction, bias, and signal quality before a setup moves into paper execution review.",
  },
  positions: {
    eyebrow: "Exposure map",
    title: "Portfolio exposure board",
    description: "Track size, concentration, and unrealized risk across the simulated portfolio inventory.",
  },
  trades: {
    eyebrow: "Execution flow",
    title: "Orders and fill stream",
    description: "Review order pressure, fills, fees, and modeled execution quality in a single workflow.",
  },
  backtests: {
    eyebrow: "Research archive",
    title: "Backtest command center",
    description: "Compare run quality, equity behavior, and research archive health before promoting an idea.",
  },
  models: {
    eyebrow: "Model stack",
    title: "Model performance board",
    description: "Monitor baseline quality, readiness, and ranking strength across the active model registry.",
  },
  logs: {
    eyebrow: "Event stream",
    title: "Operational event trail",
    description: "Audit system state, service warnings, and execution issues from one structured event surface.",
  },
  account: {
    eyebrow: "Identity layer",
    title: "Account, payouts, and access",
    description: "Manage access, Stripe readiness, and withdrawal controls without mixing paper and real cash.",
  },
  billing: {
    eyebrow: "Revenue controls",
    title: "Billing and subscription stack",
    description: "Run hosted checkout, inspect subscription state, and manage customer billing access cleanly.",
  },
  settings: {
    eyebrow: "Runtime protocol",
    title: "Runtime, providers, and controls",
    description: "Check market coverage, broker posture, and execution safeguards before changing system state.",
  },
};

function formatSummaryValue(card: SummaryCard) {
  if (typeof card.value === "string") {
    return card.value;
  }

  const label = card.label.toLowerCase();
  if (label.includes("rate") || label.includes("return") || label.includes("drawdown")) {
    return formatPercent(card.value);
  }

  return formatCurrency(card.value);
}

function formatSummaryMeta(card: SummaryCard) {
  if (card.delta == null || Number.isNaN(card.delta)) {
    return "Stored dashboard metric";
  }

  const prefix = card.delta >= 0 ? "+" : "";
  return `${prefix}${formatCurrency(card.delta)} vs previous snapshot`;
}

function getBestBacktest(backtests: DashboardBacktest[]) {
  return [...backtests].sort((left, right) => right.sharpe + right.total_return - (left.sharpe + left.total_return))[0];
}

function getHeaderCards(snapshot: DashboardSnapshot | null, runtime: RuntimeSettings | null): ShellStatCard[] {
  const tones: ShellStatCard["tone"][] = ["blue", "emerald", "amber", "slate"];

  if (snapshot?.summary_cards?.length) {
    return snapshot.summary_cards.slice(0, 4).map((card, index) => ({
      label: card.label,
      value: formatSummaryValue(card),
      meta: formatSummaryMeta(card),
      tone: tones[index % tones.length],
    }));
  }

  const openPositions = (snapshot?.positions ?? []).filter((position) => Math.abs(position.quantity) > 0).length;
  const bestBacktest = getBestBacktest(snapshot?.backtests ?? []);

  return [
    {
      label: "Signals",
      value: String(snapshot?.latest_signals.length ?? 0),
      meta: "Fresh items on the latest tape",
      tone: "blue",
    },
    {
      label: "Positions",
      value: String(openPositions),
      meta: "Open simulated exposures",
      tone: "emerald",
    },
    {
      label: "Best Sharpe",
      value: bestBacktest ? bestBacktest.sharpe.toFixed(2) : "-",
      meta: bestBacktest ? bestBacktest.name : "No stored backtest",
      tone: "amber",
    },
    {
      label: "Providers",
      value: String(runtime?.available_market_data_sources?.length ?? 0),
      meta: runtime?.available_market_data_sources?.join(" / ") ?? "Waiting for runtime settings",
      tone: "slate",
    },
  ];
}

function getInitialPage(): PageKey {
  const searchParams = new URLSearchParams(window.location.search);
  if (searchParams.get("stripe")) {
    return "account";
  }
  if (searchParams.get("billing")) {
    return "billing";
  }
  return "overview";
}

export default function App() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [runtime, setRuntime] = useState<RuntimeSettings | null>(null);
  const [brokerStatus, setBrokerStatus] = useState<BrokerStatus | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activePage, setActivePage] = useState<PageKey>(getInitialPage);

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      try {
        let user: AuthUser;
        try {
          user = await fetchCurrentUser();
        } catch (caughtError) {
          const message = caughtError instanceof Error ? caughtError.message : "Authentication unavailable.";
          if (message !== "Authentication required.") {
            throw caughtError;
          }
          const session = await refreshCurrentSession();
          user = session.user;
        }
        if (active) {
          setCurrentUser(user);
          setAuthError(null);
        }
      } catch (caughtError) {
        if (active) {
          setCurrentUser(null);
          const message = caughtError instanceof Error ? caughtError.message : "Authentication unavailable.";
          setAuthError(message === "Authentication required." ? null : message);
        }
      } finally {
        if (active) {
          setAuthLoading(false);
        }
      }
    }

    void restoreSession();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!currentUser) {
      return;
    }

    let active = true;

    async function loadData() {
      try {
        const [healthPayload, snapshotPayload, runtimePayload, brokerPayload, orderPayload, executionPayload] =
          await Promise.all([
            fetchHealth(),
            fetchDashboardSnapshot(),
            fetchRuntimeSettings(),
            fetchBrokerStatus(),
            fetchOrders(),
            fetchExecutions(),
          ]);

        if (active) {
          setHealth(healthPayload);
          setSnapshot(snapshotPayload);
          setRuntime(runtimePayload);
          setBrokerStatus(brokerPayload);
          setOrders(orderPayload);
          setExecutions(executionPayload);
          setError(null);
        }
      } catch (caughtError) {
        if (active) {
          const message = caughtError instanceof Error ? caughtError.message : "Unknown API error";
          if (message === "Authentication required.") {
            setCurrentUser(null);
            setAuthError(null);
            setSnapshot(null);
            setRuntime(null);
            setBrokerStatus(null);
            setOrders([]);
            setExecutions([]);
          } else {
            setError(message);
          }
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    setLoading(true);
    void loadData();

    return () => {
      active = false;
    };
  }, [currentUser]);

  async function handleAuthenticated(session: AuthSession) {
    setCurrentUser(session.user);
    setAuthError(null);
    setActivePage(getInitialPage());
  }

  async function handleSignOut() {
    try {
      await logoutAccount();
    } finally {
      setCurrentUser(null);
      setSnapshot(null);
      setRuntime(null);
      setBrokerStatus(null);
      setOrders([]);
      setExecutions([]);
      setError(null);
      setActivePage("overview");
    }
  }

  async function handleSeedDemo() {
    try {
      setSeeding(true);
      await seedDemoData();
      const [snapshotPayload, orderPayload, executionPayload] = await Promise.all([
        fetchDashboardSnapshot(),
        fetchOrders(),
        fetchExecutions(),
      ]);
      setSnapshot(snapshotPayload);
      setOrders(orderPayload);
      setExecutions(executionPayload);
    } catch (caughtError) {
      const message = caughtError instanceof Error ? caughtError.message : "Demo seed failed";
      if (message === "Authentication required.") {
        setCurrentUser(null);
      } else {
        setError(message);
      }
    } finally {
      setSeeding(false);
    }
  }

  function renderPage() {
    if (!currentUser) {
      return null;
    }

    switch (activePage) {
      case "signals":
        return <LiveSignals snapshot={snapshot} />;
      case "positions":
        return <Positions snapshot={snapshot} />;
      case "trades":
        return <Trades orders={orders} executions={executions} />;
      case "backtests":
        return <Backtests snapshot={snapshot} />;
      case "models":
        return <Models snapshot={snapshot} />;
      case "logs":
        return <Logs snapshot={snapshot} />;
      case "account":
        return <Account user={currentUser} />;
      case "billing":
        return <Billing />;
      case "settings":
        return (
          <Settings
            runtime={runtime}
            brokerStatus={brokerStatus}
            onSeedDemo={handleSeedDemo}
            seeding={seeding}
          />
        );
      case "overview":
      default:
        return <Overview snapshot={snapshot} runtime={runtime} loading={loading} error={error} />;
    }
  }

  if (authLoading) {
    return (
      <div className="auth-shell">
        <section className="auth-card auth-card-loading">
          <span className="eyebrow">Loading session</span>
          <h1>Checking secure access</h1>
          <p>Restoring your dashboard session and validating the database-backed login.</p>
        </section>
      </div>
    );
  }

  if (!currentUser) {
    return <AuthScreen onAuthenticated={handleAuthenticated} initialError={authError} />;
  }

  const activeCopy = pageCopy[activePage];

  return (
    <AppShell
      mode={health?.execution_mode ?? (import.meta.env.VITE_APP_MODE ?? "PAPER")}
      activePage={activePage}
      onPageChange={setActivePage}
      apiStatus={error ? "offline" : "online"}
      eyebrow={activeCopy.eyebrow}
      title={activeCopy.title}
      description={activeCopy.description}
      generatedAt={snapshot?.generated_at}
      headerCards={getHeaderCards(snapshot, runtime)}
      userLabel={currentUser.full_name ?? currentUser.email}
      onSignOut={handleSignOut}
    >
      {renderPage()}
    </AppShell>
  );
}

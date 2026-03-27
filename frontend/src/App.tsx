import { useEffect, useState } from "react";

import {
  fetchBrokerStatus,
  fetchDashboardSnapshot,
  fetchHealth,
  fetchExecutions,
  fetchOrders,
  fetchRuntimeSettings,
  seedDemoData,
} from "./api/client";
import { AppShell } from "./components/layout/AppShell";
import type { PageKey } from "./components/layout/Sidebar";
import { Backtests } from "./pages/Backtests";
import { LiveSignals } from "./pages/LiveSignals";
import { Logs } from "./pages/Logs";
import { Models } from "./pages/Models";
import { Overview } from "./pages/Overview";
import { Positions } from "./pages/Positions";
import { Settings } from "./pages/Settings";
import { Trades } from "./pages/Trades";
import type { BrokerStatus, Execution, Order } from "./types/broker";
import type { DashboardSnapshot } from "./types/dashboard";
import type { HealthResponse } from "./types/health";
import type { RuntimeSettings } from "./types/runtime";

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [runtime, setRuntime] = useState<RuntimeSettings | null>(null);
  const [brokerStatus, setBrokerStatus] = useState<BrokerStatus | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activePage, setActivePage] = useState<PageKey>("overview");

  useEffect(() => {
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
          setError(caughtError instanceof Error ? caughtError.message : "Unknown API error");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadData();

    return () => {
      active = false;
    };
  }, []);

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
      setError(caughtError instanceof Error ? caughtError.message : "Demo seed failed");
    } finally {
      setSeeding(false);
    }
  }

  function renderPage() {
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

  return (
    <AppShell
      mode={health?.execution_mode ?? (import.meta.env.VITE_APP_MODE ?? "PAPER")}
      activePage={activePage}
      onPageChange={setActivePage}
      apiStatus={error ? "offline" : "online"}
    >
      {renderPage()}
    </AppShell>
  );
}

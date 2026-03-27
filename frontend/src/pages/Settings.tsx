import { useEffect, useState } from "react";

import { fetchMarketStatus } from "../api/client";
import { ModeBadge } from "../components/status/ModeBadge";
import type { BrokerStatus } from "../types/broker";
import type { MarketStatus } from "../types/marketStatus";
import type { RuntimeSettings } from "../types/runtime";
import { formatDateTime } from "../utils/format";

type SettingsProps = {
  runtime: RuntimeSettings | null;
  brokerStatus: BrokerStatus | null;
  onSeedDemo: () => void;
  seeding: boolean;
};

export function Settings({ runtime, brokerStatus, onSeedDemo, seeding }: SettingsProps) {
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null);
  const [marketStatusError, setMarketStatusError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadMarketStatus() {
      try {
        const payload = await fetchMarketStatus("US");
        if (active) {
          setMarketStatus(payload);
          setMarketStatusError(null);
        }
      } catch (caughtError) {
        if (active) {
          setMarketStatus(null);
          setMarketStatusError(caughtError instanceof Error ? caughtError.message : "Market status unavailable.");
        }
      }
    }

    void loadMarketStatus();

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="dashboard-page">
      <div className="page-grid compact">
        <section className="panel page-panel">
          <div className="panel-header">
            <div>
              <h3>Runtime</h3>
              <p>Simulation mode, environment, and the market scope used by the research engine.</p>
            </div>
          </div>
          <div className="stack">
            <div className="setting-row">
              <span>Mode</span>
              <ModeBadge mode={runtime?.execution_mode ?? "PAPER"} />
            </div>
            <div className="setting-row">
              <span>Environment</span>
              <strong>{runtime?.environment ?? "-"}</strong>
            </div>
            <div className="setting-row">
              <span>External Broker Routing</span>
              <strong>{runtime?.live_trading_enabled ? "Enabled" : "Disabled"}</strong>
            </div>
            <div className="setting-row">
              <span>Default Symbols</span>
              <strong>{runtime?.default_symbols?.join(", ") ?? "-"}</strong>
            </div>
            <div className="setting-row">
              <span>Timeframe</span>
              <strong>{runtime?.default_timeframe ?? "-"}</strong>
            </div>
            <div className="setting-row">
              <span>Available Data Sources</span>
              <strong>{runtime?.available_market_data_sources?.join(", ") ?? "-"}</strong>
            </div>
            <div className="setting-row">
              <span>Market Status Provider</span>
              <strong>{runtime?.market_status_provider ?? "Unavailable"}</strong>
            </div>
          </div>
        </section>

        <section className="panel page-panel">
          <div className="panel-header">
            <div>
              <h3>Simulation engine</h3>
              <p>Order and fill simulation over real market data, without routing to an external broker.</p>
            </div>
          </div>
          <div className="stack">
            <div className="setting-row">
              <span>Adapter</span>
              <strong>{brokerStatus?.adapter ?? "-"}</strong>
            </div>
            <div className="setting-row">
              <span>Broker Connection</span>
              <strong>{brokerStatus?.connected ? "Reachable" : "Not in use"}</strong>
            </div>
            <p className="broker-note">{brokerStatus?.details ?? "Status unavailable."}</p>
            <button className="seed-button" onClick={onSeedDemo} type="button" disabled={seeding}>
              {seeding ? "Seeding demo..." : "Run Demo Seed"}
            </button>
          </div>
        </section>

        <section className="panel page-panel">
          <div className="panel-header">
            <div>
              <h3>US market status</h3>
              <p>Live exchange state from Finnhub so you can verify if the market is open, closed, or pre-market.</p>
            </div>
          </div>
          <div className="stack">
            <div className="setting-row">
              <span>Exchange</span>
              <strong>{marketStatus?.exchange ?? "US"}</strong>
            </div>
            <div className="setting-row">
              <span>Session</span>
              <strong>{marketStatus?.session ?? "-"}</strong>
            </div>
            <div className="setting-row">
              <span>State</span>
              <strong>{marketStatus ? (marketStatus.is_open ? "Open" : "Closed") : "-"}</strong>
            </div>
            <div className="setting-row">
              <span>Timezone</span>
              <strong>{marketStatus?.timezone ?? "-"}</strong>
            </div>
            <div className="setting-row">
              <span>Holiday</span>
              <strong>{marketStatus?.holiday ?? "None"}</strong>
            </div>
            <div className="setting-row">
              <span>Checked At</span>
              <strong>{formatDateTime(marketStatus?.timestamp)}</strong>
            </div>
            {marketStatusError ? <p className="broker-note">{marketStatusError}</p> : null}
          </div>
        </section>
      </div>
    </div>
  );
}

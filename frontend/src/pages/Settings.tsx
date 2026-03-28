import { useEffect, useState } from "react";

import { fetchMarketStatus } from "../api/client";
import { PageIntro } from "../components/page/PageIntro";
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
  const marketRegionLabel = runtime?.market_region_label ?? "Europe";
  const marketStatusExchange = runtime?.market_status_exchange ?? "EU";
  const availableSources = runtime?.available_market_data_sources ?? [];
  const brokerTone = brokerStatus?.connected ? "positive" : "neutral";
  const marketTone = marketStatus ? (marketStatus.is_open ? "positive" : "warning") : marketStatusError ? "warning" : "neutral";

  useEffect(() => {
    let active = true;

    async function loadMarketStatus() {
      try {
        const payload = await fetchMarketStatus(marketStatusExchange);
        if (active) {
          setMarketStatus(payload);
          setMarketStatusError(null);
        }
      } catch (caughtError) {
        if (active) {
          setMarketStatus(null);
          if (marketStatusExchange === "EU") {
            setMarketStatusError("Europe market status is not available with the current Finnhub key.");
          } else {
            setMarketStatusError(caughtError instanceof Error ? caughtError.message : "Market status unavailable.");
          }
        }
      }
    }

    void loadMarketStatus();

    return () => {
      active = false;
    };
  }, [marketStatusExchange]);

  return (
    <div className="dashboard-page">
      <PageIntro
        eyebrow="Runtime Controls"
        title="System runtime and market routing"
        description="Review execution safeguards, data-source coverage, broker posture, and market-session visibility before changing demo or research state."
        stats={[
          {
            label: "Execution mode",
            value: runtime?.execution_mode ?? "PAPER",
            note: runtime?.live_trading_enabled ? "External broker routing enabled" : "Paper-only safety remains active",
            tone: runtime?.live_trading_enabled ? "warning" : "positive",
          },
          {
            label: "Market region",
            value: marketRegionLabel,
            note: runtime?.default_symbols?.join(", ") ?? "No default symbols configured",
            tone: "accent",
          },
          {
            label: "Data sources",
            value: availableSources.length,
            note: availableSources.length > 0 ? availableSources.join(", ") : "No providers exposed in runtime",
            tone: availableSources.length > 0 ? "neutral" : "warning",
          },
          {
            label: "Broker posture",
            value: brokerStatus?.connected ? "Reachable" : "Idle",
            note: brokerStatus?.adapter ?? "No broker adapter reported",
            tone: brokerTone,
          },
        ]}
      />

      <section className="detail-card-grid">
        <article className="detail-card">
          <div className="detail-card-topline">
            <span className="metric-label">Execution safety</span>
            <span className={`tone-pill tone-${runtime?.live_trading_enabled ? "warning" : "positive"}`}>
              {runtime?.live_trading_enabled ? "Routing enabled" : "Paper default"}
            </span>
          </div>
          <strong>{runtime?.execution_mode ?? "PAPER"}</strong>
          <p>Production-style controls remain centered on paper trading unless live routing is explicitly turned on.</p>
          <div className="detail-card-meta">
            <span>{runtime?.environment ?? "Unknown environment"}</span>
            <span>{runtime?.default_timeframe ?? "No timeframe"}</span>
          </div>
        </article>

        <article className="detail-card">
          <div className="detail-card-topline">
            <span className="metric-label">Broker adapter</span>
            <span className={`tone-pill tone-${brokerTone}`}>{brokerStatus?.connected ? "Connected" : "Not in use"}</span>
          </div>
          <strong>{brokerStatus?.adapter ?? "Unavailable"}</strong>
          <p>{brokerStatus?.details ?? "Broker connectivity details are not available in the current snapshot."}</p>
          <div className="detail-card-meta">
            <span>{brokerStatus?.mode ?? runtime?.execution_mode ?? "PAPER"}</span>
            <span>{runtime?.broker_adapter ?? "No adapter configured"}</span>
          </div>
        </article>

        <article className="detail-card">
          <div className="detail-card-topline">
            <span className="metric-label">Market session</span>
            <span className={`tone-pill tone-${marketTone}`}>{marketStatus ? (marketStatus.is_open ? "Open" : "Closed") : "Unknown"}</span>
          </div>
          <strong>{marketStatus?.exchange ?? marketStatusExchange}</strong>
          <p>
            {marketStatus
              ? `${marketStatus.session} session in ${marketStatus.timezone}.`
              : marketStatusError ?? "No live session data is available for the configured exchange."}
          </p>
          <div className="detail-card-meta">
            <span>{marketStatus?.provider ?? runtime?.market_status_provider ?? "No provider"}</span>
            <span>{formatDateTime(marketStatus?.timestamp)}</span>
          </div>
        </article>
      </section>

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
              <strong>
                <span className={`tone-pill tone-${runtime?.live_trading_enabled ? "warning" : "positive"}`}>
                  {runtime?.live_trading_enabled ? "Enabled" : "Disabled"}
                </span>
              </strong>
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
              <span>Market Region</span>
              <strong>{marketRegionLabel}</strong>
            </div>
            <div className="setting-row">
              <span>Available Data Sources</span>
              <strong>{runtime?.available_market_data_sources?.join(", ") ?? "-"}</strong>
            </div>
            <div className="setting-row">
              <span>Market Status Provider</span>
              <strong>{runtime?.market_status_provider ?? "Unavailable"}</strong>
            </div>
            <p className="helper-note">
              This runtime is positioned for research and paper trading. Treat live routing as an explicit override, not a default operating mode.
            </p>
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
              <strong>
                <span className={`tone-pill tone-${brokerTone}`}>{brokerStatus?.connected ? "Reachable" : "Not in use"}</span>
              </strong>
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
              <h3>{marketRegionLabel} market status</h3>
              <p>Live exchange state from Finnhub for the dashboard default market region.</p>
            </div>
          </div>
          <div className="stack">
            <div className="setting-row">
              <span>Exchange</span>
              <strong>{marketStatus?.exchange ?? marketStatusExchange}</strong>
            </div>
            <div className="setting-row">
              <span>Session</span>
              <strong>{marketStatus?.session ?? "-"}</strong>
            </div>
            <div className="setting-row">
              <span>State</span>
              <strong>
                <span className={`tone-pill tone-${marketTone}`}>{marketStatus ? (marketStatus.is_open ? "Open" : "Closed") : "Unknown"}</span>
              </strong>
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
            <div className="setting-row">
              <span>Provider</span>
              <strong>{marketStatus?.provider ?? runtime?.market_status_provider ?? "-"}</strong>
            </div>
            {marketStatusError ? <p className="broker-note">{marketStatusError}</p> : null}
          </div>
        </section>
      </div>
    </div>
  );
}

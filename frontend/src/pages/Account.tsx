import { useEffect, useState } from "react";

import {
  createStripeDashboardLink,
  createStripeOnboardingLink,
  createWithdrawal,
  fetchWalletSummary,
  fetchWithdrawals,
  refreshStripeStatus,
} from "../api/client";
import { PageIntro } from "../components/page/PageIntro";
import type { AuthUser } from "../types/auth";
import type { WalletSummary, WithdrawalRequest } from "../types/wallet";
import { formatCurrency, formatDateTime } from "../utils/format";

type AccountProps = {
  user: AuthUser;
};

export function Account({ user }: AccountProps) {
  const [wallet, setWallet] = useState<WalletSummary | null>(null);
  const [withdrawals, setWithdrawals] = useState<WithdrawalRequest[]>([]);
  const [amountInput, setAmountInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadWallet() {
      try {
        setLoading(true);
        setError(null);

        const stripeFlow = new URLSearchParams(window.location.search).get("stripe");
        if (stripeFlow) {
          try {
            await refreshStripeStatus();
          } finally {
            const url = new URL(window.location.href);
            url.searchParams.delete("stripe");
            window.history.replaceState({}, document.title, `${url.pathname}${url.search}${url.hash}`);
          }
        }

        const [walletPayload, withdrawalsPayload] = await Promise.all([fetchWalletSummary(), fetchWithdrawals()]);
        if (active) {
          setWallet(walletPayload);
          setWithdrawals(withdrawalsPayload);
        }
      } catch (caughtError) {
        if (active) {
          setError(caughtError instanceof Error ? caughtError.message : "Wallet unavailable.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadWallet();

    return () => {
      active = false;
    };
  }, []);

  async function handleCreateOnboardingLink() {
    try {
      setError(null);
      const payload = await createStripeOnboardingLink();
      window.location.assign(payload.url);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Could not start Stripe onboarding.");
    }
  }

  async function handleRefreshStripe() {
    try {
      setError(null);
      const payload = await refreshStripeStatus();
      setWallet(payload);
      setSuccess("Stripe status updated.");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Could not refresh Stripe status.");
    }
  }

  async function handleOpenStripeDashboard() {
    try {
      setError(null);
      const payload = await createStripeDashboardLink();
      window.open(payload.url, "_blank", "noopener,noreferrer");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Could not open Stripe dashboard.");
    }
  }

  async function handleWithdraw() {
    const amount = Math.round(Number.parseFloat(amountInput.replace(",", ".")) * 100);
    if (!Number.isFinite(amount) || amount <= 0) {
      setError("Enter a valid withdrawal amount.");
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      setSuccess(null);

      const created = await createWithdrawal(amount);
      const [walletPayload, withdrawalsPayload] = await Promise.all([fetchWalletSummary(), fetchWithdrawals()]);
      setWallet(walletPayload);
      setWithdrawals([created, ...withdrawalsPayload.filter((item) => item.id !== created.id)]);
      setAmountInput("");
      setSuccess("Withdrawal request submitted.");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Withdrawal request failed.");
    } finally {
      setSubmitting(false);
    }
  }

  const summary = wallet ?? {
    withdrawable_balance_cents: user.withdrawable_balance_cents,
    currency: user.currency,
    withdrawals_enabled: false,
    stripe: {
      account_id: user.stripe_connected_account_id,
      onboarding_complete: user.stripe_onboarding_complete,
      transfers_enabled: user.stripe_transfers_enabled,
      requirements_status: null,
      capability_status: null,
      dashboard_access: Boolean(user.stripe_connected_account_id),
    },
  };
  const pendingWithdrawals = withdrawals.filter((item) => /pending|queued|processing/i.test(item.status)).length;
  const latestWithdrawal = [...withdrawals].sort((left, right) => right.created_at.localeCompare(left.created_at))[0] ?? null;
  const stripeStatusTone = getStripeTone(summary.stripe);
  const identityTone = "positive";

  return (
    <div className="dashboard-page">
      <PageIntro
        eyebrow="Account Center"
        title="Identity, payouts, and cash access"
        description="Manage the authenticated operator profile, Stripe Connect readiness, and withdrawal flow without mixing simulated PnL with real cash operations."
        stats={[
          {
            label: "Account role",
            value: user.role,
            note: user.is_active ? "Session is active in the current dashboard" : "User is currently disabled",
            tone: user.is_active ? "positive" : "negative",
          },
          {
            label: "Account status",
            value: "Ready",
            note: "Direct sign-in enabled",
            tone: identityTone,
          },
          {
            label: "Withdrawable balance",
            value: formatCurrency(summary.withdrawable_balance_cents / 100, summary.currency),
            note: `${pendingWithdrawals} withdrawal requests still in-flight`,
            tone: summary.withdrawals_enabled ? "accent" : "neutral",
          },
          {
            label: "Stripe Connect",
            value: summary.stripe.transfers_enabled ? "Ready" : summary.stripe.account_id ? "In progress" : "Not linked",
            note: summary.stripe.account_id ?? "No connected account yet",
            tone: stripeStatusTone,
          },
        ]}
      />

      <section className="detail-card-grid">
        <article className="detail-card">
          <div className="detail-card-topline">
            <span className="metric-label">Identity</span>
            <span className={`tone-pill tone-${identityTone}`}>{user.is_active ? "Active" : "Disabled"}</span>
          </div>
          <strong>{user.full_name ?? user.email}</strong>
          <p>The authenticated session controls payout access, Stripe onboarding actions, and withdrawal requests.</p>
          <div className="detail-card-meta">
            <span>{user.email}</span>
            <span>Direct sign-in enabled</span>
          </div>
        </article>

        <article className="detail-card">
          <div className="detail-card-topline">
            <span className="metric-label">Stripe readiness</span>
            <span className={`tone-pill tone-${stripeStatusTone}`}>{summary.stripe.transfers_enabled ? "Payout ready" : "Needs action"}</span>
          </div>
          <strong>{summary.stripe.account_id ?? "No Stripe account connected"}</strong>
          <p>
            {summary.stripe.transfers_enabled
              ? "Transfers can be enabled from the connected Stripe account when withdrawals are turned on."
              : "Finish onboarding and requirements review before treating this account as payout-capable."}
          </p>
          <div className="detail-card-meta">
            <span>{summary.stripe.requirements_status ?? "No requirements state yet"}</span>
            <span>{summary.stripe.capability_status ?? "Capabilities pending"}</span>
          </div>
        </article>

        <article className="detail-card">
          <div className="detail-card-topline">
            <span className="metric-label">Latest withdrawal</span>
            <span className={`tone-pill ${latestWithdrawal ? getWithdrawalTone(latestWithdrawal.status) : "tone-neutral"}`}>
              {latestWithdrawal?.status ?? "None"}
            </span>
          </div>
          <strong>
            {latestWithdrawal ? formatCurrency(latestWithdrawal.amount_cents / 100, latestWithdrawal.currency) : "No requests"}
          </strong>
          <p>
            {latestWithdrawal
              ? "Recent request recorded in the database and linked to payout/transfer references when available."
              : "Withdrawal history will appear here after a request is created."}
          </p>
          <div className="detail-card-meta">
            <span>{latestWithdrawal ? formatDateTime(latestWithdrawal.created_at) : "Waiting for activity"}</span>
            <span>{latestWithdrawal?.stripe_payout_id ?? latestWithdrawal?.stripe_transfer_id ?? "No Stripe reference"}</span>
          </div>
        </article>
      </section>

      <div className="page-grid compact">
        <section className="panel page-panel">
          <div className="panel-header">
            <div>
              <h3>Account access</h3>
              <p>Real user session, role, and Stripe payout identity connected to the dashboard.</p>
            </div>
          </div>
          <div className="stack">
            <div className="setting-row">
              <span>User</span>
              <strong>{user.full_name ?? user.email}</strong>
            </div>
            <div className="setting-row">
              <span>Email</span>
              <strong>{user.email}</strong>
            </div>
            <div className="setting-row">
              <span>Role</span>
              <strong>
                <span className="tone-pill tone-accent">{user.role}</span>
              </strong>
            </div>
            <div className="setting-row">
              <span>Session state</span>
              <strong>
                <span className={`tone-pill tone-${user.is_active ? "positive" : "negative"}`}>
                  {user.is_active ? "Active" : "Disabled"}
                </span>
              </strong>
            </div>
            <div className="setting-row">
              <span>Access policy</span>
              <strong>
                <span className={`tone-pill tone-${identityTone}`}>Direct sign-in</span>
              </strong>
            </div>
            <div className="setting-row">
              <span>Last login</span>
              <strong>{formatDateTime(user.last_login_at)}</strong>
            </div>
          </div>
        </section>

        <section className="panel page-panel">
          <div className="panel-header">
            <div>
              <h3>Withdrawals</h3>
              <p>Only withdrawable cash can be requested here. Simulated PnL is not treated as real cash.</p>
            </div>
          </div>
          <div className="stack">
            <div className="setting-row">
              <span>Withdrawable balance</span>
              <strong>{formatCurrency(summary.withdrawable_balance_cents / 100, summary.currency)}</strong>
            </div>
            <div className="setting-row">
              <span>Currency</span>
              <strong>{summary.currency.toUpperCase()}</strong>
            </div>
            <div className="setting-row">
              <span>Withdrawal engine</span>
              <strong>
                <span className={`tone-pill tone-${summary.withdrawals_enabled ? "positive" : "neutral"}`}>
                  {summary.withdrawals_enabled ? "Enabled" : "Disabled by default"}
                </span>
              </strong>
            </div>
            <label className="auth-field slim">
              <span>Amount ({summary.currency.toUpperCase()})</span>
              <input
                inputMode="decimal"
                onChange={(event) => setAmountInput(event.target.value)}
                placeholder="250.00"
                type="text"
                value={amountInput}
              />
            </label>
            <p className="helper-note">
              Only ledger cash marked as withdrawable can be requested here. Paper-trading PnL remains isolated from payouts.
            </p>
            <button className="seed-button" disabled={loading || submitting} onClick={handleWithdraw} type="button">
              {submitting ? "Submitting..." : "Request withdrawal"}
            </button>
          </div>
        </section>

        <section className="panel page-panel">
          <div className="panel-header">
            <div>
              <h3>Stripe Connect</h3>
              <p>Onboard the payout account, sync requirements, and open the Stripe Express dashboard.</p>
            </div>
          </div>
          <div className="stack">
            <div className="setting-row">
              <span>Connected account</span>
              <strong>{summary.stripe.account_id ?? "Not linked"}</strong>
            </div>
            <div className="setting-row">
              <span>Onboarding</span>
              <strong>
                <span className={`tone-pill tone-${summary.stripe.onboarding_complete ? "positive" : "warning"}`}>
                  {summary.stripe.onboarding_complete ? "Completed" : "Pending"}
                </span>
              </strong>
            </div>
            <div className="setting-row">
              <span>Transfers capability</span>
              <strong>
                <span className={`tone-pill tone-${summary.stripe.transfers_enabled ? "positive" : "warning"}`}>
                  {summary.stripe.transfers_enabled ? "Active" : "Not ready"}
                </span>
              </strong>
            </div>
            <div className="setting-row">
              <span>Requirements status</span>
              <strong>{summary.stripe.requirements_status ?? "-"}</strong>
            </div>
            <p className="helper-note">
              Stripe Connect has to be fully onboarded before this account can move from identity setup into payout readiness.
            </p>
            <div className="action-row">
              <button className="primary-button" onClick={handleCreateOnboardingLink} type="button">
                {summary.stripe.account_id ? "Continue Stripe onboarding" : "Connect Stripe account"}
              </button>
              <button className="ghost-button" onClick={handleRefreshStripe} type="button">
                Refresh Stripe status
              </button>
              <button
                className="ghost-button"
                disabled={!summary.stripe.dashboard_access}
                onClick={handleOpenStripeDashboard}
                type="button"
              >
                Open Stripe dashboard
              </button>
            </div>
          </div>
        </section>

        <section className="panel page-panel page-panel-wide">
          <div className="panel-header">
            <div>
              <h3>Recent withdrawal requests</h3>
              <p>Requests are stored in the database and linked to Stripe transfer and payout identifiers.</p>
            </div>
          </div>

          {error ? <p className="auth-error">{error}</p> : null}
          {success ? <p className="auth-success">{success}</p> : null}

          <div className="withdrawal-list">
            {withdrawals.length ? (
              withdrawals.map((item) => (
                <article className="withdrawal-card" key={item.id}>
                  <div>
                    <span className="eyebrow">Request #{item.id}</span>
                    <strong>{formatCurrency(item.amount_cents / 100, item.currency)}</strong>
                  </div>
                  <div className="withdrawal-meta">
                    <span className={`tone-pill ${getWithdrawalTone(item.status)}`}>{item.status}</span>
                    <span>{formatDateTime(item.created_at)}</span>
                    <span>{item.processed_at ? `Processed ${formatDateTime(item.processed_at)}` : "Waiting for processing"}</span>
                    <span>{item.failure_message ?? item.stripe_payout_id ?? item.stripe_transfer_id ?? "-"}</span>
                  </div>
                </article>
              ))
            ) : (
              <p className="broker-note">
            {loading ? "Loading wallet..." : "No withdrawal requests recorded for this account yet."}
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function getStripeTone(stripe: WalletSummary["stripe"]): "neutral" | "positive" | "warning" | "accent" {
  if (stripe.transfers_enabled) {
    return "positive";
  }
  if (stripe.account_id && stripe.onboarding_complete) {
    return "accent";
  }
  if (stripe.account_id) {
    return "warning";
  }
  return "neutral";
}

function getWithdrawalTone(status: string) {
  const normalizedStatus = status.toLowerCase();
  if (normalizedStatus.includes("paid") || normalizedStatus.includes("complete") || normalizedStatus.includes("success")) {
    return "tone-positive";
  }
  if (normalizedStatus.includes("fail") || normalizedStatus.includes("cancel") || normalizedStatus.includes("rejected")) {
    return "tone-negative";
  }
  if (normalizedStatus.includes("pending") || normalizedStatus.includes("queue") || normalizedStatus.includes("process")) {
    return "tone-warning";
  }
  return "tone-accent";
}

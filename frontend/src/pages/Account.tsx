import { useEffect, useState } from "react";

import {
  createStripeDashboardLink,
  createStripeOnboardingLink,
  createWithdrawal,
  fetchWalletSummary,
  fetchWithdrawals,
  refreshStripeStatus,
} from "../api/client";
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

  return (
    <div className="dashboard-page">
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
              <strong>{user.role}</strong>
            </div>
            <div className="setting-row">
              <span>Session state</span>
              <strong>{user.is_active ? "Active" : "Disabled"}</strong>
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
              <strong>{formatCurrency(summary.withdrawable_balance_cents / 100)}</strong>
            </div>
            <div className="setting-row">
              <span>Currency</span>
              <strong>{summary.currency.toUpperCase()}</strong>
            </div>
            <div className="setting-row">
              <span>Withdrawal engine</span>
              <strong>{summary.withdrawals_enabled ? "Enabled" : "Disabled by default"}</strong>
            </div>
            <label className="auth-field slim">
              <span>Amount (USD)</span>
              <input
                inputMode="decimal"
                onChange={(event) => setAmountInput(event.target.value)}
                placeholder="250.00"
                type="text"
                value={amountInput}
              />
            </label>
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
              <strong>{summary.stripe.onboarding_complete ? "Completed" : "Pending"}</strong>
            </div>
            <div className="setting-row">
              <span>Transfers capability</span>
              <strong>{summary.stripe.transfers_enabled ? "Active" : "Not ready"}</strong>
            </div>
            <div className="setting-row">
              <span>Requirements status</span>
              <strong>{summary.stripe.requirements_status ?? "-"}</strong>
            </div>
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
                    <strong>{formatCurrency(item.amount_cents / 100)}</strong>
                  </div>
                  <div className="withdrawal-meta">
                    <span>{item.status}</span>
                    <span>{formatDateTime(item.created_at)}</span>
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

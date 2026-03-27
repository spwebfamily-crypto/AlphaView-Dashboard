import { useEffect, useState } from "react";

import {
  createBillingCheckoutSession,
  createBillingPortalSession,
  fetchBillingSummary,
} from "../api/client";
import type { BillingSummary } from "../types/billing";
import { formatDateTime } from "../utils/format";

const DEFAULT_PRICE_ID = "price_demo_starter";

export function Billing() {
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [priceId, setPriceId] = useState(DEFAULT_PRICE_ID);
  const [planCode, setPlanCode] = useState("starter");
  const [mode, setMode] = useState<"payment" | "subscription">("subscription");
  const [quantity, setQuantity] = useState("1");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadBillingSummary() {
      try {
        setLoading(true);
        setError(null);

        const billingFlow = new URLSearchParams(window.location.search).get("billing");
        if (billingFlow && active) {
          if (billingFlow === "success") {
            setSuccess("Stripe Checkout returned successfully. Billing state will refresh after the webhook lands.");
          } else if (billingFlow === "cancel") {
            setSuccess("Checkout was canceled before payment confirmation.");
          } else if (billingFlow === "portal") {
            setSuccess("Returned from the Stripe Billing Portal.");
          }

          const url = new URL(window.location.href);
          url.searchParams.delete("billing");
          window.history.replaceState({}, document.title, `${url.pathname}${url.search}${url.hash}`);
        }

        const payload = await fetchBillingSummary();
        if (active) {
          setSummary(payload);
        }
      } catch (caughtError) {
        if (active) {
          setError(caughtError instanceof Error ? caughtError.message : "Billing is unavailable.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadBillingSummary();

    return () => {
      active = false;
    };
  }, []);

  async function handleCheckout() {
    const normalizedQuantity = Number.parseInt(quantity, 10);
    if (!priceId.trim()) {
      setError("Enter a Stripe price id before creating Checkout.");
      return;
    }
    if (!Number.isFinite(normalizedQuantity) || normalizedQuantity <= 0) {
      setError("Quantity must be a positive integer.");
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      const payload = await createBillingCheckoutSession({
        price_id: priceId.trim(),
        mode,
        quantity: normalizedQuantity,
        plan_code: planCode.trim() || undefined,
      });
      window.location.assign(payload.url);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Could not create a Stripe Checkout session.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleOpenPortal() {
    try {
      setSubmitting(true);
      setError(null);
      const payload = await createBillingPortalSession();
      window.open(payload.url, "_blank", "noopener,noreferrer");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Could not open the Stripe Billing Portal.");
    } finally {
      setSubmitting(false);
    }
  }

  const currentSummary = summary ?? {
    stripe_customer_id: null,
    stripe_subscription_id: null,
    billing_status: null,
    billing_plan_code: null,
    billing_current_period_end: null,
    checkout_ready: false,
    portal_ready: false,
  };

  return (
    <div className="dashboard-page">
      <div className="page-grid compact">
        <section className="panel page-panel">
          <div className="panel-header">
            <div>
              <h3>Billing status</h3>
              <p>Local subscription state synced from Stripe Checkout and webhook events.</p>
            </div>
          </div>
          <div className="stack">
            <div className="setting-row">
              <span>Stripe customer</span>
              <strong>{currentSummary.stripe_customer_id ?? "Not linked yet"}</strong>
            </div>
            <div className="setting-row">
              <span>Subscription</span>
              <strong>{currentSummary.stripe_subscription_id ?? "No active subscription"}</strong>
            </div>
            <div className="setting-row">
              <span>Status</span>
              <strong>{currentSummary.billing_status ?? "-"}</strong>
            </div>
            <div className="setting-row">
              <span>Plan</span>
              <strong>{currentSummary.billing_plan_code ?? "-"}</strong>
            </div>
            <div className="setting-row">
              <span>Current period end</span>
              <strong>{formatDateTime(currentSummary.billing_current_period_end)}</strong>
            </div>
          </div>
        </section>

        <section className="panel page-panel">
          <div className="panel-header">
            <div>
              <h3>Stripe Checkout</h3>
              <p>Create a hosted checkout session for a one-time payment or subscription plan.</p>
            </div>
          </div>
          <div className="stack">
            <div className="action-row">
              <button
                className={`ghost-button ${mode === "subscription" ? "active" : ""}`}
                onClick={() => setMode("subscription")}
                type="button"
              >
                Subscription
              </button>
              <button
                className={`ghost-button ${mode === "payment" ? "active" : ""}`}
                onClick={() => setMode("payment")}
                type="button"
              >
                One-time payment
              </button>
            </div>
            <label className="auth-field slim">
              <span>Stripe price id</span>
              <input onChange={(event) => setPriceId(event.target.value)} type="text" value={priceId} />
            </label>
            <label className="auth-field slim">
              <span>Plan code</span>
              <input onChange={(event) => setPlanCode(event.target.value)} placeholder="starter" type="text" value={planCode} />
            </label>
            <label className="auth-field slim">
              <span>Quantity</span>
              <input inputMode="numeric" onChange={(event) => setQuantity(event.target.value)} type="text" value={quantity} />
            </label>
            <button
              className="primary-button"
              disabled={loading || submitting || !currentSummary.checkout_ready}
              onClick={handleCheckout}
              type="button"
            >
              {submitting ? "Opening Checkout..." : "Open Stripe Checkout"}
            </button>
          </div>
        </section>

        <section className="panel page-panel">
          <div className="panel-header">
            <div>
              <h3>Customer portal</h3>
              <p>Open the Stripe Billing Portal for an already-linked customer.</p>
            </div>
          </div>
          <div className="stack">
            <div className="setting-row">
              <span>Portal ready</span>
              <strong>{currentSummary.portal_ready ? "Ready" : "Waiting for Stripe customer"}</strong>
            </div>
            <button
              className="ghost-button"
              disabled={loading || submitting || !currentSummary.portal_ready}
              onClick={handleOpenPortal}
              type="button"
            >
              Open Billing Portal
            </button>
          </div>
        </section>

        <section className="panel page-panel page-panel-wide">
          <div className="panel-header">
            <div>
              <h3>Operator notes</h3>
              <p>Use the hosted Stripe flows. The dashboard state updates after the Stripe webhook is accepted by the backend.</p>
            </div>
          </div>

          {error ? <p className="auth-error">{error}</p> : null}
          {success ? <p className="auth-success">{success}</p> : null}

          <div className="stack">
            <div className="setting-row">
              <span>Checkout API</span>
              <strong>/api/v1/billing/checkout-session</strong>
            </div>
            <div className="setting-row">
              <span>Portal API</span>
              <strong>/api/v1/billing/portal-session</strong>
            </div>
            <div className="setting-row">
              <span>Webhook sync</span>
              <strong>/api/v1/billing/webhook</strong>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

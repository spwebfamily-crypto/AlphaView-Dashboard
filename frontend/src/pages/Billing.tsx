import { useEffect, useState } from "react";

import {
  createBillingCheckoutSession,
  createBillingPortalSession,
  fetchBillingSummary,
} from "../api/client";
import { PageIntro } from "../components/page/PageIntro";
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
  const billingTone = getBillingTone(currentSummary.billing_status);
  const currentPlanLabel = currentSummary.billing_plan_code ?? "No plan";
  const currentModeLabel = mode === "subscription" ? "Recurring plan" : "One-time payment";

  return (
    <div className="dashboard-page">
      <PageIntro
        eyebrow="Revenue Layer"
        title="Billing and subscription controls"
        description="Manage customer billing state, Stripe Checkout launch parameters, and portal access from the same commercial control surface."
        stats={[
          {
            label: "Billing state",
            value: currentSummary.billing_status ?? "Unlinked",
            note: currentSummary.stripe_customer_id ?? "No Stripe customer linked yet",
            tone: billingTone,
          },
          {
            label: "Active plan",
            value: currentPlanLabel,
            note: currentSummary.billing_current_period_end
              ? `Renews or ends ${formatDateTime(currentSummary.billing_current_period_end)}`
              : "No active billing cycle stored",
            tone: currentSummary.billing_plan_code ? "accent" : "neutral",
          },
          {
            label: "Checkout launch",
            value: currentSummary.checkout_ready ? "Ready" : "Blocked",
            note: currentModeLabel,
            tone: currentSummary.checkout_ready ? "positive" : "warning",
          },
          {
            label: "Portal access",
            value: currentSummary.portal_ready ? "Available" : "Waiting",
            note: currentSummary.portal_ready ? "Customer can manage billing in Stripe" : "Stripe customer required first",
            tone: currentSummary.portal_ready ? "positive" : "neutral",
          },
        ]}
      />

      <section className="detail-card-grid">
        <article className="detail-card">
          <div className="detail-card-topline">
            <span className="metric-label">Customer record</span>
            <span className={`tone-pill tone-${currentSummary.stripe_customer_id ? "positive" : "neutral"}`}>
              {currentSummary.stripe_customer_id ? "Linked" : "Missing"}
            </span>
          </div>
          <strong>{currentSummary.stripe_customer_id ?? "No Stripe customer"}</strong>
          <p>Portal access and subscription lifecycle management depend on a linked Stripe customer record.</p>
          <div className="detail-card-meta">
            <span>{currentSummary.portal_ready ? "Portal can be opened" : "Portal still unavailable"}</span>
            <span>{currentSummary.stripe_subscription_id ?? "No subscription id"}</span>
          </div>
        </article>

        <article className="detail-card">
          <div className="detail-card-topline">
            <span className="metric-label">Checkout mode</span>
            <span className={`tone-pill tone-${mode === "subscription" ? "accent" : "warning"}`}>{currentModeLabel}</span>
          </div>
          <strong>{priceId || "Price id required"}</strong>
          <p>Use hosted Stripe Checkout for safer payment collection and keep the dashboard synchronized through webhooks.</p>
          <div className="detail-card-meta">
            <span>{planCode || "No plan code set"}</span>
            <span>{quantity} unit(s)</span>
          </div>
        </article>

        <article className="detail-card">
          <div className="detail-card-topline">
            <span className="metric-label">Billing lifecycle</span>
            <span className={`tone-pill tone-${billingTone}`}>{currentSummary.billing_status ?? "Unlinked"}</span>
          </div>
          <strong>{currentPlanLabel}</strong>
          <p>The dashboard mirrors Stripe state after webhook confirmation, so commercial state stays auditable and centralized.</p>
          <div className="detail-card-meta">
            <span>{currentSummary.billing_current_period_end ? formatDateTime(currentSummary.billing_current_period_end) : "No period end"}</span>
            <span>{currentSummary.stripe_subscription_id ?? "No subscription"}</span>
          </div>
        </article>
      </section>

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
              <strong>
                <span className={`tone-pill tone-${billingTone}`}>{currentSummary.billing_status ?? "Unlinked"}</span>
              </strong>
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
            <div className="field-grid">
              <label className="auth-field slim">
                <span>Stripe price id</span>
                <input onChange={(event) => setPriceId(event.target.value)} type="text" value={priceId} />
              </label>
              <label className="auth-field slim">
                <span>Plan code</span>
                <input onChange={(event) => setPlanCode(event.target.value)} placeholder="starter" type="text" value={planCode} />
              </label>
            </div>
            <label className="auth-field slim">
              <span>Quantity</span>
              <input inputMode="numeric" onChange={(event) => setQuantity(event.target.value)} type="text" value={quantity} />
            </label>
            <p className="helper-note">
              Hosted Checkout is the recommended commercial path. The local summary updates after the Stripe webhook lands in the backend.
            </p>
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
              <strong>
                <span className={`tone-pill tone-${currentSummary.portal_ready ? "positive" : "warning"}`}>
                  {currentSummary.portal_ready ? "Ready" : "Waiting for Stripe customer"}
                </span>
              </strong>
            </div>
            <p className="helper-note">
              The Billing Portal only makes sense after a Stripe customer exists and the commercial record is linked.
            </p>
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

          <div className="endpoint-grid">
            <article className="endpoint-card">
              <span className="metric-label">Checkout API</span>
              <strong>/api/v1/billing/checkout-session</strong>
              <p>Creates the hosted Stripe Checkout session used by the commercial flow.</p>
            </article>
            <article className="endpoint-card">
              <span className="metric-label">Portal API</span>
              <strong>/api/v1/billing/portal-session</strong>
              <p>Opens the customer-facing Stripe portal once a billing identity exists.</p>
            </article>
            <article className="endpoint-card">
              <span className="metric-label">Webhook sync</span>
              <strong>/api/v1/billing/webhook</strong>
              <p>Pushes Stripe lifecycle changes back into the dashboard billing summary.</p>
            </article>
          </div>
        </section>
      </div>
    </div>
  );
}

function getBillingTone(status: string | null): "neutral" | "positive" | "negative" | "accent" | "warning" {
  const normalizedStatus = status?.toLowerCase() ?? "";
  if (!normalizedStatus) {
    return "neutral";
  }
  if (normalizedStatus.includes("active") || normalizedStatus.includes("paid") || normalizedStatus.includes("trial")) {
    return "positive";
  }
  if (normalizedStatus.includes("past_due") || normalizedStatus.includes("incomplete") || normalizedStatus.includes("unpaid")) {
    return "warning";
  }
  if (normalizedStatus.includes("canceled") || normalizedStatus.includes("failed")) {
    return "negative";
  }
  return "accent";
}

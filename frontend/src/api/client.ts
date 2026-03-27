import type { AuthRegistrationChallenge, AuthSession, AuthUser } from "../types/auth";
import type { BillingPortalSessionPayload, BillingSummary, CheckoutSessionPayload } from "../types/billing";
import type { BrokerStatus, Execution, Order } from "../types/broker";
import type { DashboardSnapshot } from "../types/dashboard";
import type { HealthResponse } from "../types/health";
import type { MarketBar, StreamPreview } from "../types/marketData";
import type { MarketStatus } from "../types/marketStatus";
import type { RuntimeSettings } from "../types/runtime";
import type { WalletSummary, WithdrawalRequest } from "../types/wallet";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/$/, "");

let refreshInFlight: Promise<void> | null = null;

async function attemptRefresh(): Promise<void> {
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${apiBaseUrl}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Authentication required.");
        }
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }

  return refreshInFlight;
}

async function apiFetch<T>(
  path: string,
  init?: RequestInit,
  options?: { retryOnAuth?: boolean },
): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (response.status === 401 && options?.retryOnAuth !== false && !path.startsWith("/auth/")) {
    await attemptRefresh();
    return apiFetch<T>(path, init, { retryOnAuth: false });
  }

  if (!response.ok) {
    let detail = `${path} failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // Keep the fallback message.
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function buildQuery(params: Record<string, string | number | undefined>) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) {
      searchParams.set(key, String(value));
    }
  });

  return searchParams.toString();
}

export async function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

export async function registerAccount(payload: {
  email: string;
  password: string;
  full_name?: string;
}): Promise<AuthRegistrationChallenge> {
  return apiFetch<AuthRegistrationChallenge>(
    "/auth/register",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    { retryOnAuth: false },
  );
}

export async function loginAccount(payload: { email: string; password: string }): Promise<AuthSession> {
  return apiFetch<AuthSession>(
    "/auth/login",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    { retryOnAuth: false },
  );
}

export async function verifyEmailCode(payload: { email: string; code: string }): Promise<AuthSession> {
  return apiFetch<AuthSession>(
    "/auth/verify-email",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    { retryOnAuth: false },
  );
}

export async function resendVerificationCode(payload: { email: string }): Promise<AuthRegistrationChallenge> {
  return apiFetch<AuthRegistrationChallenge>(
    "/auth/resend-verification",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    { retryOnAuth: false },
  );
}

export async function logoutAccount(): Promise<void> {
  await apiFetch<{ message: string }>(
    "/auth/logout",
    {
      method: "POST",
    },
    { retryOnAuth: false },
  );
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  return apiFetch<AuthUser>("/auth/me", undefined, { retryOnAuth: false });
}

export async function refreshCurrentSession(): Promise<AuthSession> {
  return apiFetch<AuthSession>(
    "/auth/refresh",
    {
      method: "POST",
    },
    { retryOnAuth: false },
  );
}

export async function fetchDashboardSnapshot(): Promise<DashboardSnapshot> {
  return apiFetch<DashboardSnapshot>("/demo/snapshot");
}

export async function seedDemoData(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>("/demo/seed", {
    method: "POST",
    body: JSON.stringify({
      symbols: ["AAPL", "MSFT", "NVDA"],
      timeframe: "1min",
      days: 5,
    }),
  });
}

export async function fetchRuntimeSettings(): Promise<RuntimeSettings> {
  return apiFetch<RuntimeSettings>("/settings/runtime");
}

export async function fetchBrokerStatus(): Promise<BrokerStatus> {
  return apiFetch<BrokerStatus>("/broker/status");
}

export async function fetchOrders(): Promise<Order[]> {
  return apiFetch<Order[]>("/broker/orders");
}

export async function fetchExecutions(): Promise<Execution[]> {
  return apiFetch<Execution[]>("/broker/executions");
}

export async function fetchMarketBars(symbol: string, timeframe = "1min", limit = 72): Promise<MarketBar[]> {
  const query = buildQuery({
    symbol: symbol.toUpperCase(),
    timeframe,
    limit,
  });

  return apiFetch<MarketBar[]>(`/market-data/bars?${query}`);
}

export async function fetchMarketPreview(symbol: string, timeframe = "1min", points = 72): Promise<StreamPreview> {
  const query = buildQuery({
    symbol: symbol.toUpperCase(),
    timeframe,
    points,
  });

  return apiFetch<StreamPreview>(`/market-data/stream/preview?${query}`);
}

export async function fetchMarketStatus(exchange = "US"): Promise<MarketStatus> {
  const query = buildQuery({ exchange: exchange.toUpperCase() });
  return apiFetch<MarketStatus>(`/market-data/market-status?${query}`);
}

export async function fetchWalletSummary(): Promise<WalletSummary> {
  return apiFetch<WalletSummary>("/wallet/summary");
}

export async function fetchWithdrawals(): Promise<WithdrawalRequest[]> {
  return apiFetch<WithdrawalRequest[]>("/wallet/withdrawals");
}

export async function createStripeOnboardingLink(): Promise<{ url: string }> {
  return apiFetch<{ url: string }>("/wallet/stripe/onboarding-link", {
    method: "POST",
  });
}

export async function refreshStripeStatus(): Promise<WalletSummary> {
  return apiFetch<WalletSummary>("/wallet/stripe/refresh", {
    method: "POST",
  });
}

export async function createStripeDashboardLink(): Promise<{ url: string }> {
  return apiFetch<{ url: string }>("/wallet/stripe/dashboard-link", {
    method: "POST",
  });
}

export async function createWithdrawal(amountCents: number): Promise<WithdrawalRequest> {
  return apiFetch<WithdrawalRequest>("/wallet/withdrawals", {
    method: "POST",
    body: JSON.stringify({ amount_cents: amountCents }),
  });
}

export async function fetchBillingSummary(): Promise<BillingSummary> {
  return apiFetch<BillingSummary>("/billing/summary");
}

export async function createBillingCheckoutSession(payload: {
  price_id: string;
  mode: "payment" | "subscription";
  quantity: number;
  plan_code?: string;
}): Promise<CheckoutSessionPayload> {
  return apiFetch<CheckoutSessionPayload>("/billing/checkout-session", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createBillingPortalSession(): Promise<BillingPortalSessionPayload> {
  return apiFetch<BillingPortalSessionPayload>("/billing/portal-session", {
    method: "POST",
  });
}

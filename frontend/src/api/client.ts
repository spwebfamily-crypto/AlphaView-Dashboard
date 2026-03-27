import type { BrokerStatus, Execution, Order } from "../types/broker";
import type { DashboardSnapshot } from "../types/dashboard";
import type { HealthResponse } from "../types/health";
import type { MarketBar, StreamPreview } from "../types/marketData";
import type { MarketStatus } from "../types/marketStatus";
import type { RuntimeSettings } from "../types/runtime";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/$/, "");

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`${path} failed with status ${response.status}`);
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

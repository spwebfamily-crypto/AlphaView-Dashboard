export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  environment: string;
  execution_mode: string;
  live_trading_enabled: boolean;
  database: string;
};


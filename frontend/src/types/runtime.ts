export type RuntimeSettings = {
  project_name: string;
  environment: string;
  execution_mode: string;
  live_trading_enabled: boolean;
  broker_adapter: string;
  market_region_label: string;
  market_status_exchange: string;
  default_symbols: string[];
  default_timeframe: string;
  available_market_data_sources: string[];
  market_status_provider: string | null;
};

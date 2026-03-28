export type MarketBar = {
  symbol: string;
  timeframe: string;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  vwap?: number | null;
  trades_count?: number | null;
};

export type StreamPreview = {
  symbol: string;
  timeframe: string;
  source: string;
  bars: MarketBar[];
};

export type TrackedSymbol = {
  ticker: string;
  name: string | null;
  exchange: string | null;
  asset_type: string;
  is_active: boolean;
  market?: string | null;
  primary_exchange?: string | null;
  security_type?: string | null;
  currency?: string | null;
  round_lot_size?: number | null;
  minimum_order_size?: number | null;
  last_updated_utc?: string | null;
  last_price?: number | null;
  change?: number | null;
  change_percent?: number | null;
  quote_timestamp?: string | null;
  quote_source?: string | null;
};

export type MarketUniversePage = {
  items: TrackedSymbol[];
  next_cursor: string | null;
  source: string;
  as_of: string;
};

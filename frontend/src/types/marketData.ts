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

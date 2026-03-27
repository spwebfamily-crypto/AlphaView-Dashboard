export type SummaryCard = {
  label: string;
  value: number | string;
  delta?: number | null;
};

export type CurvePoint = {
  timestamp: string;
  equity?: number;
  drawdown?: number;
  pnl?: number;
};

export type DistributionPoint = {
  label: string;
  value: number;
};

export type LatestSignal = {
  symbol: string;
  timestamp: string;
  signal_type: string;
  confidence?: number | null;
  reason?: string | null;
};

export type DashboardPosition = {
  symbol?: string;
  quantity: number;
  average_price?: number | null;
  market_value?: number | null;
  unrealized_pnl?: number | null;
  status: string;
};

export type DashboardBacktest = {
  id: number;
  name: string;
  status: string;
  total_return: number;
  sharpe: number;
  trade_count: number;
};

export type DashboardModel = {
  id: number;
  name: string;
  model_type: string;
  status: string;
  f1: number;
  roc_auc: number;
};

export type DashboardLog = {
  timestamp: string;
  level: string;
  message: string;
};

export type DashboardSnapshot = {
  generated_at: string;
  mode: string;
  summary_cards: SummaryCard[];
  equity_curve: CurvePoint[];
  pnl_curve: CurvePoint[];
  win_loss_distribution: DistributionPoint[];
  latest_signals: LatestSignal[];
  positions: DashboardPosition[];
  backtests: DashboardBacktest[];
  models: DashboardModel[];
  logs: DashboardLog[];
};


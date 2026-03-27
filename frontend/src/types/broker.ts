export type BrokerStatus = {
  adapter: string;
  mode: string;
  connected: boolean;
  details: string;
};

export type Order = {
  id: number;
  symbol: string;
  side: string;
  order_type: string;
  quantity: number;
  limit_price?: number | null;
  status: string;
  mode: string;
  submitted_at?: string | null;
};

export type Execution = {
  id: number;
  order_id: number;
  executed_at: string;
  price: number;
  quantity: number;
  fees?: number | null;
};


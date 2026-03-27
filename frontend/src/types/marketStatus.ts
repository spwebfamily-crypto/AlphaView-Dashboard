export type MarketStatus = {
  exchange: string;
  holiday: string | null;
  is_open: boolean;
  session: string;
  timezone: string;
  timestamp: string;
  provider: string;
};

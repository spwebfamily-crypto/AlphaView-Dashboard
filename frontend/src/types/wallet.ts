export type StripeConnectStatus = {
  account_id: string | null;
  onboarding_complete: boolean;
  transfers_enabled: boolean;
  requirements_status: string | null;
  capability_status: string | null;
  dashboard_access: boolean;
};

export type WalletSummary = {
  withdrawable_balance_cents: number;
  currency: string;
  withdrawals_enabled: boolean;
  stripe: StripeConnectStatus;
};

export type WithdrawalRequest = {
  id: number;
  amount_cents: number;
  currency: string;
  status: string;
  stripe_account_id: string | null;
  stripe_transfer_id: string | null;
  stripe_payout_id: string | null;
  failure_code: string | null;
  failure_message: string | null;
  processed_at: string | null;
  created_at: string;
  updated_at: string;
};

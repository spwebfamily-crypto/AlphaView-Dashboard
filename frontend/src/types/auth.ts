export type AuthUser = {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  currency: string;
  withdrawable_balance_cents: number;
  stripe_connected_account_id: string | null;
  stripe_onboarding_complete: boolean;
  stripe_transfers_enabled: boolean;
  last_login_at: string | null;
};

export type AuthSession = {
  user: AuthUser;
  access_token_expires_in_seconds: number;
  refresh_token_expires_in_seconds: number;
};

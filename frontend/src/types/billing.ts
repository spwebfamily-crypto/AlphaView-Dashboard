export type BillingSummary = {
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  billing_status: string | null;
  billing_plan_code: string | null;
  billing_current_period_end: string | null;
  checkout_ready: boolean;
  portal_ready: boolean;
};

export type CheckoutSessionPayload = {
  session_id: string;
  url: string;
};

export type BillingPortalSessionPayload = {
  url: string;
};

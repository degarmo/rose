import { post, request } from './api'
import { formatMoney } from './format'

export type TierInterval = 'month' | 'year' | 'once'

export interface Tier {
  slug: string
  name: string
  description: string
  benefits: string[]
  price_cents: number
  currency: string
  interval: TierInterval
  interval_label: string
  duration_days: number | null
  grants_feed_access: boolean
  grants_members_events: boolean
  grants_members_education: boolean
  /** A one-night guest pass, paid at the door. Offered on /guests, not with memberships. */
  is_guest_pass: boolean
  /** Development-only demo tier; never offered with DEBUG off. */
  is_placeholder: boolean
}

export interface Agreement {
  version: number
  title: string
  body: string
  published_at: string
  is_placeholder: boolean
}

export interface PaymentMethod {
  key: string
  label: string
  online: boolean
}

export interface JoinOptions {
  methods: PaymentMethod[]
  agreement: Agreement | null
}

export type MembershipStatus = 'pending_payment' | 'active' | 'grace' | 'expired' | 'cancelled' | 'suspended'

export interface PaymentSummary {
  id: number
  created_at: string
  amount_cents: number
  method: 'cash' | 'card_in_person' | 'online' | 'comp'
  method_label: string
  status: 'succeeded' | 'refunded' | 'failed'
  status_label: string
}

export interface MyMembership {
  reference_code: string
  tier: Tier
  status: MembershipStatus
  status_label: string
  current_period_start: string | null
  current_period_end: string | null
  auto_renew: boolean
  cancel_at_period_end: boolean
  paid_awaiting_id_check: boolean
  source: 'manual' | 'provider' | 'comp'
  online: boolean
  id_checked: boolean
  last_payment_failed: boolean
  /** Unpaid reference codes lapse; null once paid or running. */
  code_expires_at: string | null
  payments: PaymentSummary[]
  created_at: string
}

export type Entitlement = 'feed' | 'members_events' | 'members_education'

export interface MembershipPayload {
  membership: MyMembership | null
  entitlements: Entitlement[]
}

export interface JoinResult extends MembershipPayload {
  redirect_url: string | null
}

export interface Receipt {
  title: string
  merchant: string
  description: string
  reference: string
  date: string
  amount_cents: number
  currency: string
  method: string
  kind: 'Payment' | 'Refund'
}

export interface SandboxSession {
  amount_cents: number
  reference: string
  /** What the payment is for, in one neutral word: "Membership" or "Donation". */
  description: string
  interval: TierInterval
}

export const OPEN_STATUSES: MembershipStatus[] = ['pending_payment', 'active', 'grace', 'suspended']

export function isOpen(membership: MyMembership | null): membership is MyMembership {
  return membership !== null && OPEN_STATUSES.includes(membership.status)
}

export const membershipApi = {
  tiers: () => request<Tier[]>('/membership/tiers/'),
  options: () => request<JoinOptions>('/membership/options/'),
  me: () => request<MembershipPayload>('/membership/me/'),
  join: (payload: { tier: string; agreement_version: number; typed_name: string; method: string }) =>
    post<JoinResult>('/membership/join/', payload),
  checkout: (method: string) => post<{ redirect_url: string }>('/membership/checkout/', { method }),
  cancel: () => post<MembershipPayload>('/membership/cancel/'),
  setAutoRenew: (enabled: boolean) => post<MembershipPayload>('/membership/auto-renew/', { enabled }),
  receipt: (paymentId: string) => request<Receipt>(`/membership/receipts/${encodeURIComponent(paymentId)}/`),
  sandboxSession: (token: string) => request<SandboxSession>(`/payments/sandbox/${encodeURIComponent(token)}/`),
  sandboxOutcome: (token: string, outcome: 'pay' | 'fail' | 'cancel') =>
    post<{ redirect_url: string }>(`/payments/sandbox/${encodeURIComponent(token)}/`, { outcome }),
}

/** Full-page navigation to a provider's hosted checkout (or back from it). */
export function goTo(url: string) {
  window.location.assign(url)
}

export function priceLabel(tier: Tier) {
  const price = formatMoney(tier.price_cents, tier.currency)
  if (tier.interval === 'month') return `${price} a month`
  if (tier.interval === 'year') return `${price} a year`
  const days = tier.duration_days ?? 30
  return `${price} for ${days} ${days === 1 ? 'day' : 'days'}`
}

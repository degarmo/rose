import { post, request } from './api'
import { formatMoney } from './format'

export type TierInterval = 'month' | 'year' | 'once'

export interface EventTag {
  slug: string
  name: string
}

export interface Tier {
  slug: string
  name: string
  /** One line under the price. */
  description: string
  perks: string[]
  price_cents: number
  currency: string
  is_free: boolean
  interval: TierInterval
  interval_label: string
  duration_days: number | null
  renews: boolean
  /** Members-only events each calendar month; null is unlimited. */
  events_per_month: number | null
  guests_included_per_event: number
  guest_discount: boolean
  premium_discord: boolean
  /** "tagged": only members-only events carrying one of `allowed_event_tags`. */
  event_access: 'all' | 'tagged'
  allowed_event_tags: EventTag[]
  grants_feed_access: boolean
  grants_members_events: boolean
  grants_members_education: boolean
  /** Highlighted as "Most popular". */
  is_featured: boolean
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
  /** Your own members-only events left this month while the membership runs; null is unlimited. */
  events_remaining_this_month: number | null
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
  /** A free tier needs no method. */
  join: (payload: { tier: string; agreement_version: number; typed_name: string; method?: string }) =>
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

/** "1 week", "2 weeks", "1 day", "30 days". */
export function durationLabel(days: number) {
  if (days % 7 === 0) return days === 7 ? '1 week' : `${days / 7} weeks`
  return days === 1 ? '1 day' : `${days} days`
}

export function priceLabel(tier: Tier) {
  const length = durationLabel(tier.duration_days ?? 30)
  if (tier.is_free) return tier.interval === 'once' ? `Free for ${length}` : 'Free'
  const price = formatMoney(tier.price_cents, tier.currency)
  if (tier.interval === 'month') return `${price} a month`
  if (tier.interval === 'year') return `${price} a year`
  return `${price} for ${length}`
}

/** Beside the big price: "/ month", "one-time · 2 weeks", "free · 1 week" or "free". */
export function billingLabel(tier: Tier) {
  const length = durationLabel(tier.duration_days ?? 30)
  if (tier.is_free) return tier.interval === 'once' ? `free · ${length}` : 'free'
  if (tier.interval === 'month') return '/ month'
  if (tier.interval === 'year') return '/ year'
  return `one-time · ${length}`
}

/** "1 event left this month", or "Unlimited events this month", for a running membership. */
export function eventsLeftLabel(membership: MyMembership) {
  const left = membership.events_remaining_this_month
  if (left === null) return 'Unlimited events this month'
  return `${left} ${left === 1 ? 'event' : 'events'} left this month`
}

/** Membership tiers in the order the API gives them (price, then the staff's sort order). */
export function membershipTiers(tiers: Tier[]) {
  return tiers.filter((tier) => !tier.is_guest_pass)
}

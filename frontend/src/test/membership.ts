import type { Agreement, MyMembership, Tier } from '@/lib/membershipApi'

export function makeTier(overrides: Partial<Tier> = {}): Tier {
  return {
    slug: 'monthly',
    name: 'Monthly',
    description: 'Renews every month.',
    perks: ['Members-only nights', 'Members-only classes'],
    price_cents: 2500,
    currency: 'USD',
    is_free: false,
    interval: 'month',
    interval_label: 'Monthly',
    duration_days: null,
    renews: true,
    events_per_month: null,
    guests_included_per_event: 0,
    guest_discount: false,
    premium_discord: false,
    event_access: 'all',
    allowed_event_tags: [],
    grants_feed_access: true,
    grants_members_events: true,
    grants_members_education: true,
    is_featured: false,
    is_guest_pass: false,
    is_placeholder: false,
    ...overrides,
  }
}

export const agreement: Agreement = {
  version: 3,
  title: 'Membership agreement',
  body: '<p>I agree to the community agreements.</p><ul><li>Consent first.</li></ul>',
  published_at: '2026-10-01T12:00:00Z',
  is_placeholder: false,
}

export function makeMembership(overrides: Partial<MyMembership> = {}): MyMembership {
  return {
    reference_code: 'R7K-42Q',
    tier: makeTier(),
    status: 'pending_payment',
    status_label: 'Waiting for payment',
    current_period_start: null,
    current_period_end: null,
    auto_renew: false,
    cancel_at_period_end: false,
    paid_awaiting_id_check: false,
    source: 'manual',
    online: false,
    id_checked: false,
    last_payment_failed: false,
    code_expires_at: '2026-11-17T12:00:00Z',
    payments: [],
    events_remaining_this_month: null,
    created_at: '2026-10-18T12:00:00Z',
    ...overrides,
  }
}

import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PageCopy } from '@/lib/pageContent'
import { makeMembership, makeTier } from '@/test/membership'
import { renderWithProviders, verifiedUser } from '@/test/render'
import { MembershipPage } from './MembershipPage'

const api = vi.hoisted(() => ({ tiers: vi.fn(), me: vi.fn() }))

vi.mock('@/lib/membershipApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membershipApi')>()
  return { ...actual, membershipApi: { ...actual.membershipApi, tiers: api.tiers, me: api.me } }
})

const COPY: Record<string, string> = {
  'hero.title': 'Find the membership that fits.',
  'hero.lede': 'Monthly plans renew each month, and you can cancel any time.',
  'compare.title': 'Compare plans',
  'good_to_know.title': 'Good to know',
  'good_to_know.1': 'Cancel any time by emailing us.',
  'good_to_know.2': 'Bringing someone? Guest prices are on the Guests page.',
  tip: "Use an email address that doesn't include your legal name.",
  'cta.title': 'Ready for a first visit?',
  'cta.button': 'Plan your visit',
  newsletter: 'Occasional news, never more than monthly.',
}

vi.mock('@/lib/pageContent', () => ({
  usePageContent: (): PageCopy => ({
    status: 'success',
    retry: () => undefined,
    entry: (key) => (COPY[key] ? { value: COPY[key], format: 'plain' } : null),
    text: (key) => COPY[key] ?? '',
    items: (prefix) => (prefix === 'good_to_know' ? [1, 2] : []),
  }),
}))

// The API's order (price, then sort order). The page must keep it, not re-sort it.
const TIERS = [
  makeTier({ slug: 'community', name: 'Community', price_cents: 0, is_free: true, renews: true, event_access: 'tagged', allowed_event_tags: [{ slug: 'community', name: 'Community' }], grants_feed_access: false, perks: ['Education nights'] }),
  makeTier({ slug: 'first-fridays', name: 'First Fridays', price_cents: 0, is_free: true, interval: 'once', duration_days: 7, renews: false, events_per_month: 1, grants_feed_access: false }),
  makeTier({ slug: 'limited', name: 'Limited', price_cents: 2000, events_per_month: 1, premium_discord: true }),
  makeTier({ slug: 'trial', name: 'Trial', price_cents: 2000, interval: 'once', duration_days: 14, renews: false }),
  makeTier({ slug: 'limited-plus', name: 'Limited +', price_cents: 3500, events_per_month: 1, guests_included_per_event: 1 }),
  makeTier({ slug: 'rose', name: 'Rose', price_cents: 4000, guest_discount: true, premium_discord: true, is_featured: true }),
  makeTier({ slug: 'rose-plus', name: 'Rose +', price_cents: 5500, guests_included_per_event: 1, guest_discount: true }),
  makeTier({ slug: 'guest-night', name: 'Guest night pass', price_cents: 1500, interval: 'once', duration_days: 1, is_guest_pass: true }),
]
const ORDER = ['Community', 'First Fridays', 'Limited', 'Trial', 'Limited +', 'Rose', 'Rose +']

beforeEach(() => {
  api.tiers.mockReset().mockResolvedValue(TIERS)
  api.me.mockReset().mockResolvedValue({ membership: null, entitlements: [] })
})

function cards() {
  return within(screen.getByRole('region', { name: 'Plans' })).getAllByRole('listitem').filter((item) => item.querySelector('h2'))
}

describe('MembershipPage', () => {
  it('lists every membership in the API order, with prices and billing labels', async () => {
    renderWithProviders(<MembershipPage />)
    expect(await screen.findByRole('heading', { level: 1, name: 'Find the membership that fits.' })).toBeInTheDocument()
    await screen.findByRole('heading', { level: 2, name: 'Rose +' })
    expect(cards().map((card) => card.querySelector('h2')?.textContent)).toEqual(ORDER)
    const [community, firstFridays, limited, trial] = cards()
    expect(community).toHaveTextContent('$0free')
    expect(firstFridays).toHaveTextContent('$0free · 1 week')
    expect(limited).toHaveTextContent('$20/ month')
    expect(trial).toHaveTextContent('$20one-time · 2 weeks')
    expect(screen.queryByText('Guest night pass')).not.toBeInTheDocument()
  })

  it('features Rose without moving it, and every Choose goes to the join flow', async () => {
    renderWithProviders(<MembershipPage />)
    const rose = (await screen.findByRole('heading', { level: 2, name: 'Rose' })).closest('li')!
    expect(within(rose).getByText('Most popular')).toBeInTheDocument()
    expect(screen.getAllByText('Most popular')).toHaveLength(1)
    expect(screen.getByRole('link', { name: 'Choose Limited' })).toHaveAttribute('href', '/join?tier=limited')
    expect(screen.getByRole('link', { name: 'Choose Rose +' })).toHaveAttribute('href', '/join?tier=rose-plus')
  })

  it('compares the plans in the same order', async () => {
    renderWithProviders(<MembershipPage />)
    const table = await screen.findByRole('table')
    const headers = within(table).getAllByRole('columnheader').map((cell) => cell.textContent)
    expect(headers).toEqual(ORDER)
    const rows = within(table).getAllByRole('rowheader').map((cell) => cell.textContent)
    expect(rows).toEqual(['Price', 'Renews', 'Events per month', 'Guests included', 'Guest discount', 'Premium Discord', 'Member community', 'Which events'])
    const events = within(table).getByRole('rowheader', { name: 'Which events' }).closest('tr')!
    expect(events).toHaveTextContent('Community events')
    expect(events).toHaveTextContent('All club events')
    const perMonth = within(table).getByRole('rowheader', { name: 'Events per month' }).closest('tr')!
    expect(perMonth).toHaveTextContent('Unlimited')
    // Phones get one short list per tier instead of a wide table.
    expect(screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)).toEqual(ORDER)
  })

  it('has the staff-editable good-to-know list, the email tip and the way on', async () => {
    renderWithProviders(<MembershipPage />)
    expect(await screen.findByRole('heading', { name: 'Good to know' })).toBeInTheDocument()
    expect(screen.getByText('Cancel any time by emailing us.')).toBeInTheDocument()
    expect(within(screen.getByRole('complementary', { name: 'Tip' })).getByText(/legal name/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Plan your visit' })).toHaveAttribute('href', '/visit')
    expect(screen.getByLabelText('Occasional news, never more than monthly.')).toBeInTheDocument()
  })

  it('shows members their plan, its dates and the events left this month', async () => {
    const limited = TIERS[2]
    api.me.mockResolvedValue({
      membership: makeMembership({
        tier: limited,
        status: 'active',
        status_label: 'Active',
        current_period_end: '2026-11-18T12:00:00Z',
        events_remaining_this_month: 0,
        code_expires_at: null,
      }),
      entitlements: ['feed'],
    })
    renderWithProviders(<MembershipPage />, { user: { ...verifiedUser, has_membership: true } })
    const banner = await screen.findByRole('region', { name: 'Your membership' })
    expect(banner).toHaveTextContent('Your plan: Limited')
    expect(banner).toHaveTextContent('Renews November 18, 2026')
    expect(banner).toHaveTextContent('0 events left this month')
    expect(within(banner).getByRole('link', { name: 'Manage' })).toHaveAttribute('href', '/members/settings/membership')
    const card = (await screen.findByRole('heading', { level: 2, name: 'Limited' })).closest('li')!
    expect(within(card).getByText('Your plan')).toBeInTheDocument()
    expect(within(card).queryByRole('link', { name: 'Choose Limited' })).not.toBeInTheDocument()
  })

  it('shows no banner for a membership that is not running', async () => {
    api.me.mockResolvedValue({ membership: makeMembership({ status: 'expired', status_label: 'Expired' }), entitlements: [] })
    renderWithProviders(<MembershipPage />, { user: { ...verifiedUser, has_membership: true } })
    await screen.findByRole('heading', { level: 2, name: 'Rose' })
    expect(screen.queryByRole('region', { name: 'Your membership' })).not.toBeInTheDocument()
    expect(screen.queryByText('Your plan')).not.toBeInTheDocument()
  })

  it('says so when no plans are on offer, instead of an empty page', async () => {
    api.tiers.mockResolvedValue([])
    renderWithProviders(<MembershipPage />)
    expect(await screen.findByText('Membership plans are not online yet')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByText('Membership plans did not load')).not.toBeInTheDocument()
  })

  it('says the plans did not load when the request fails', async () => {
    api.tiers.mockRejectedValue(new Error('Server error'))
    renderWithProviders(<MembershipPage />)
    expect(await screen.findByText('Membership plans did not load')).toBeInTheDocument()
  })
})

import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { makeMembership } from '@/test/membership'
import { renderWithProviders, verifiedUser } from '@/test/render'
import { MembershipCard } from './MembershipCard'

const api = vi.hoisted(() => ({ me: vi.fn(), cancel: vi.fn(), setAutoRenew: vi.fn() }))

vi.mock('@/lib/membershipApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membershipApi')>()
  return { ...actual, membershipApi: { ...actual.membershipApi, ...api } }
})

const member = { ...verifiedUser, has_membership: true }

const active = makeMembership({
  status: 'active',
  status_label: 'Active',
  current_period_start: '2026-10-13T12:00:00Z',
  current_period_end: '2026-11-12T12:00:00Z',
  code_expires_at: null,
  id_checked: true,
  payments: [
    { id: 41, created_at: '2026-10-13T12:00:00Z', amount_cents: 2500, method: 'cash', method_label: 'Cash', status: 'succeeded', status_label: 'Succeeded' },
    { id: 40, created_at: '2026-09-02T12:00:00Z', amount_cents: 2500, method: 'online', method_label: 'Online', status: 'failed', status_label: 'Failed' },
  ],
})

beforeEach(() => Object.values(api).forEach((fn) => fn.mockReset()))

describe('MembershipCard', () => {
  it('invites people without a membership to join', async () => {
    api.me.mockResolvedValue({ membership: null, entitlements: [] })
    renderWithProviders(<MembershipCard />, { user: verifiedUser })
    expect(await screen.findByText(/You are not a member yet/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Become a member' })).toHaveAttribute('href', '/join')
  })

  it('shows a pending code with what to bring', async () => {
    api.me.mockResolvedValue({ membership: makeMembership(), entitlements: [] })
    renderWithProviders(<MembershipCard />, { user: member })
    expect(await screen.findByText('Waiting for payment')).toBeInTheDocument()
    expect(screen.getByText('R7K-42Q')).toBeInTheDocument()
    expect(await screen.findByAltText('QR code for R7K-42Q')).toBeInTheDocument()
    expect(screen.getByText(/Your payment: \$25 a month/)).toBeInTheDocument()
    expect(screen.getByText(/stays open until November 17, 2026/)).toBeInTheDocument()
    expect(screen.queryByRole('switch')).not.toBeInTheDocument()
  })

  it('shows an active in-person membership with payments and receipts', async () => {
    api.me.mockResolvedValue({ membership: active, entitlements: ['feed', 'members_events', 'members_education'] })
    renderWithProviders(<MembershipCard />, { user: member })
    expect(await screen.findByText('Paid through November 12, 2026')).toBeInTheDocument()
    expect(screen.getByText('Active')).toBeInTheDocument()
    const receipts = screen.getAllByRole('link', { name: 'Receipt' })
    expect(receipts).toHaveLength(1)
    expect(receipts[0]).toHaveAttribute('href', '/account/receipts/41')
    expect(screen.getByText(/Failed payment/)).toBeInTheDocument()
    expect(screen.queryByRole('switch')).not.toBeInTheDocument() // in person: no auto-renew
  })

  it('lets online members turn automatic renewal off', async () => {
    const online = { ...active, source: 'provider' as const, online: true, auto_renew: true }
    api.me.mockResolvedValue({ membership: online, entitlements: [] })
    api.setAutoRenew.mockResolvedValue({ membership: { ...online, auto_renew: false, cancel_at_period_end: true }, entitlements: [] })
    renderWithProviders(<MembershipCard />, { user: member })
    const toggle = await screen.findByRole('switch', { name: /Renew automatically/ })
    expect(toggle).toBeChecked()
    expect(screen.getByText('Renews automatically on November 12, 2026')).toBeInTheDocument()
    await userEvent.click(toggle)
    await waitFor(() => expect(api.setAutoRenew).toHaveBeenCalledWith(false))
    expect(await screen.findByText('Ends November 12, 2026. It will not renew.')).toBeInTheDocument()
  })

  it('confirms before cancelling', async () => {
    api.me.mockResolvedValue({ membership: active, entitlements: [] })
    api.cancel.mockResolvedValue({ membership: { ...active, cancel_at_period_end: true }, entitlements: [] })
    renderWithProviders(<MembershipCard />, { user: member })
    await userEvent.click(await screen.findByRole('button', { name: 'Cancel membership' }))
    expect(api.cancel).not.toHaveBeenCalled()
    const dialog = screen.getByRole('dialog', { name: 'Cancel your membership?', hidden: true })
    expect(within(dialog).getByText(/You keep access until November 12, 2026/)).toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    expect(api.cancel).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Cancel membership' }))
    await userEvent.click(within(dialog).getByRole('button', { name: 'Cancel at period end' }))
    await waitFor(() => expect(api.cancel).toHaveBeenCalledOnce())
    expect(await screen.findByText('Ends November 12, 2026. It will not renew.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cancel membership' })).not.toBeInTheDocument()
  })

  it('offers to join again after expiry, without a code', async () => {
    api.me.mockResolvedValue({
      membership: { ...active, status: 'expired', status_label: 'Expired' },
      entitlements: [],
    })
    renderWithProviders(<MembershipCard />, { user: member })
    expect(await screen.findByText('Ended November 12, 2026')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Join again' })).toHaveAttribute('href', '/join')
    expect(screen.queryByText('R7K-42Q')).not.toBeInTheDocument()
  })

  it('shows paid-awaiting-ID without asking for payment again', async () => {
    api.me.mockResolvedValue({
      membership: makeMembership({ paid_awaiting_id_check: true, code_expires_at: null }),
      entitlements: [],
    })
    renderWithProviders(<MembershipCard />, { user: member })
    expect(await screen.findByText(/Paid. Staff will start your membership after a quick photo ID check/)).toBeInTheDocument()
    expect(screen.queryByText(/Your payment:/)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cancel membership' })).not.toBeInTheDocument()
  })

  it('shows an error with retry', async () => {
    api.me.mockRejectedValueOnce(new Error('offline'))
    api.me.mockResolvedValue({ membership: null, entitlements: [] })
    renderWithProviders(<MembershipCard />, { user: verifiedUser })
    await userEvent.click(await screen.findByRole('button', { name: 'Try again' }))
    expect(await screen.findByText(/You are not a member yet/)).toBeInTheDocument()
  })
})

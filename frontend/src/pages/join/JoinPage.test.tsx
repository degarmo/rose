import { fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { agreement, makeMembership, makeTier } from '@/test/membership'
import { renderWithProviders, unverifiedUser, verifiedUser } from '@/test/render'
import { JoinPage } from './JoinPage'

const api = vi.hoisted(() => ({
  tiers: vi.fn(),
  options: vi.fn(),
  me: vi.fn(),
  join: vi.fn(),
  goTo: vi.fn(),
}))

vi.mock('@/lib/membershipApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membershipApi')>()
  return {
    ...actual,
    goTo: api.goTo,
    membershipApi: { ...actual.membershipApi, tiers: api.tiers, options: api.options, me: api.me, join: api.join },
  }
})

const manualOnly = { methods: [{ key: 'manual', label: 'Pay at your first visit', online: false }], agreement }
const withOnline = {
  methods: [...manualOnly.methods, { key: 'sandbox', label: 'Pay online (sandbox)', online: true }],
  agreement,
}

beforeEach(() => {
  Object.values(api).forEach((fn) => fn.mockReset())
  api.tiers.mockResolvedValue([makeTier(), makeTier({ slug: 'annual', name: 'Annual', price_cents: 25000, interval: 'year' })])
  api.options.mockResolvedValue(manualOnly)
  api.me.mockResolvedValue({ membership: null, entitlements: [] })
})

/** jsdom has no layout, so tell the agreement box it was scrolled to the end. */
function scrollToEnd() {
  const region = screen.getByRole('region', { name: 'Agreement text' })
  Object.defineProperty(region, 'scrollHeight', { configurable: true, value: 1200 })
  Object.defineProperty(region, 'clientHeight', { configurable: true, value: 400 })
  region.scrollTop = 800
  fireEvent.scroll(region)
}

async function toAgreement() {
  await userEvent.click(await screen.findByRole('button', { name: 'Choose Monthly' }))
  expect(screen.getByRole('heading', { name: 'Membership agreement' })).toBeInTheDocument()
}

describe('JoinPage', () => {
  it('goes from tier to agreement to a reference code', async () => {
    api.join.mockResolvedValue({
      membership: makeMembership(),
      entitlements: [],
      redirect_url: null,
    })
    renderWithProviders(<JoinPage />, { user: verifiedUser })
    expect(await screen.findByText('$25 a month')).toBeInTheDocument()
    expect(screen.getByText('$250 a year')).toBeInTheDocument()
    await toAgreement()
    scrollToEnd()
    await userEvent.click(screen.getByLabelText('I have read and agree'))
    await userEvent.type(screen.getByLabelText(/Your full name/), '  Jordan   Q. Realname ')
    await userEvent.click(screen.getByRole('button', { name: 'Sign and continue' }))

    expect(screen.getByRole('heading', { name: 'How would you like to pay?' })).toBeInTheDocument()
    expect(screen.getByLabelText(/Pay at your first visit/)).toBeChecked()
    await userEvent.click(screen.getByRole('button', { name: 'Get my reference code' }))

    await waitFor(() =>
      expect(api.join).toHaveBeenCalledWith({ tier: 'monthly', agreement_version: 3, typed_name: 'Jordan Q. Realname', method: 'manual' }),
    )
    expect(await screen.findByRole('heading', { name: 'You are almost a member' })).toBeInTheDocument()
    expect(screen.getByText('R7K-42Q')).toBeInTheDocument()
    expect(await screen.findByAltText('QR code for R7K-42Q')).toHaveAttribute('src', expect.stringMatching(/^data:image\/svg\+xml/))
    expect(screen.getByText(/valid photo ID showing you are 18 or older/)).toBeInTheDocument()
    expect(screen.getByText(/stays open until November 17, 2026/)).toBeInTheDocument()
    expect(screen.queryByText(/Realname/)).not.toBeInTheDocument()
  })

  it('will not sign until the agreement is read, ticked and signed', async () => {
    renderWithProviders(<JoinPage />, { user: verifiedUser })
    await toAgreement()
    const tick = screen.getByLabelText('I have read and agree')
    const name = screen.getByLabelText(/Your full name/)
    const submit = screen.getByRole('button', { name: 'Sign and continue' })
    expect(tick).toBeDisabled()
    expect(name).toBeDisabled()
    expect(submit).toBeDisabled()
    expect(screen.getByText('Scroll to the end to continue.')).toBeInTheDocument()

    scrollToEnd()
    expect(screen.getByText('You have reached the end.')).toBeInTheDocument()
    expect(tick).toBeEnabled()
    expect(submit).toBeDisabled()
    await userEvent.click(tick)
    expect(name).toBeEnabled()
    expect(submit).toBeDisabled()
    await userEvent.type(name, 'J')
    expect(submit).toBeDisabled()
    await userEvent.type(name, 'o')
    expect(submit).toBeEnabled()
    expect(api.join).not.toHaveBeenCalled()
  })

  it('sends online payments to the checkout, never activating here', async () => {
    api.options.mockResolvedValue(withOnline)
    api.join.mockResolvedValue({
      membership: makeMembership({ source: 'provider' }),
      entitlements: [],
      redirect_url: 'https://site.example/dev/checkout/abc',
    })
    renderWithProviders(<JoinPage />, { user: verifiedUser })
    await toAgreement()
    scrollToEnd()
    await userEvent.click(screen.getByLabelText('I have read and agree'))
    await userEvent.type(screen.getByLabelText(/Your full name/), 'Jo Doe')
    await userEvent.click(screen.getByRole('button', { name: 'Sign and continue' }))
    await userEvent.click(screen.getByLabelText(/Pay online \(sandbox\)/))
    await userEvent.click(screen.getByRole('button', { name: 'Continue to checkout' }))
    await waitFor(() => expect(api.goTo).toHaveBeenCalledWith('https://site.example/dev/checkout/abc'))
    expect(api.join).toHaveBeenCalledWith(expect.objectContaining({ method: 'sandbox' }))
    expect(screen.queryByText('You are almost a member')).not.toBeInTheDocument()
  })

  it('asks anonymous visitors to create an account first', async () => {
    renderWithProviders(<JoinPage />)
    expect(await screen.findByRole('link', { name: 'Create an account' })).toHaveAttribute('href', '/account/register?next=%2Fjoin')
    expect(screen.getByRole('button', { name: 'Choose Monthly' })).toBeDisabled()
    expect(api.me).not.toHaveBeenCalled()
  })

  it('asks unverified accounts to confirm their email', async () => {
    renderWithProviders(<JoinPage />, { user: unverifiedUser })
    expect(await screen.findByText(/Confirm your email first/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Choose Monthly' })).toBeDisabled()
  })

  it('shows an existing membership instead of the flow', async () => {
    api.me.mockResolvedValue({ membership: makeMembership({ status: 'active', status_label: 'Active' }), entitlements: ['feed'] })
    renderWithProviders(<JoinPage />, { user: { ...verifiedUser, has_membership: true } })
    expect(await screen.findByRole('heading', { name: 'You already have a membership' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Choose Monthly' })).not.toBeInTheDocument()
  })

  it('says when joining online is not open yet', async () => {
    api.options.mockResolvedValue({ ...manualOnly, agreement: null })
    renderWithProviders(<JoinPage />, { user: verifiedUser })
    expect(await screen.findByText('Joining online is not open yet')).toBeInTheDocument()
  })

  it('reassures after a cancelled checkout', async () => {
    renderWithProviders(<JoinPage />, { user: verifiedUser, path: '/join?cancelled=1' })
    expect(await screen.findByText(/nothing was charged/)).toBeInTheDocument()
  })

  it('shows an error with retry when options fail to load', async () => {
    api.tiers.mockRejectedValueOnce(new Error('offline'))
    renderWithProviders(<JoinPage />, { user: verifiedUser })
    expect(await screen.findByText('Membership options did not load')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('button', { name: 'Choose Monthly' })).toBeEnabled()
  })
})

import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { DonationOptions } from '@/lib/api'
import { renderWithProviders, verifiedUser } from '@/test/render'
import { DonationForm } from './DonatePage'
import { amountError, parseAmount } from './donationAmount'

const mocks = vi.hoisted(() => ({ start: vi.fn(), goTo: vi.fn() }))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return { ...actual, api: { ...actual.api, startDonation: mocks.start } }
})
vi.mock('@/lib/membershipApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membershipApi')>()
  return { ...actual, goTo: mocks.goTo }
})

const options: DonationOptions = {
  online: true,
  presets_cents: [2500, 5000, 10000, 25000],
  minimum_cents: 500,
  maximum_cents: 1_000_000,
  nonprofit_status: 'A volunteer-run 501(c)(3) nonprofit.',
  check_payable_to: 'Example',
  mailing_address: 'PO Box 1',
}

beforeEach(() => {
  mocks.start.mockReset()
  mocks.goTo.mockReset()
  mocks.start.mockResolvedValue({ redirect_url: 'https://checkout.example/session' })
})

describe('parseAmount', () => {
  it('reads dollars as cents', () => {
    expect(parseAmount('30')).toBe(3000)
    expect(parseAmount('$1,250.50')).toBe(125050)
    expect(parseAmount('12.345')).toBeNull()
    expect(parseAmount('ten')).toBeNull()
  })

  it('enforces the minimum and maximum', () => {
    expect(amountError(499, 500, 1_000_000)).toMatch('$5')
    expect(amountError(500, 500, 1_000_000)).toBeUndefined()
    expect(amountError(2_000_000, 500, 1_000_000)).toMatch('get in touch')
  })
})

describe('DonationForm', () => {
  it('offers the presets and gives the chosen one', async () => {
    renderWithProviders(<DonationForm options={options} />)
    for (const label of ['$25', '$50', '$100', '$250', 'Other']) {
      expect(screen.getByRole('radio', { name: label })).toBeInTheDocument()
    }
    expect(screen.getByRole('radio', { name: '$50' })).toBeChecked()
    await userEvent.click(screen.getByRole('radio', { name: '$100' }))
    await userEvent.click(screen.getByRole('button', { name: 'Give $100' }))
    await waitFor(() => expect(mocks.start).toHaveBeenCalled())
    expect(mocks.start).toHaveBeenCalledWith({ amount_cents: 10000, email: '', show_name: false, website: '' })
    expect(mocks.goTo).toHaveBeenCalledWith('https://checkout.example/session')
  })

  it('takes a custom amount and refuses less than the minimum', async () => {
    renderWithProviders(<DonationForm options={options} />)
    await userEvent.click(screen.getByRole('radio', { name: 'Other' }))
    const amount = screen.getByLabelText(/Your amount, in dollars/)
    await userEvent.type(amount, '3')
    await userEvent.click(screen.getByRole('button', { name: 'Give' }))
    expect(screen.getByText('The smallest gift we can take online is $5.')).toBeInTheDocument()
    expect(mocks.start).not.toHaveBeenCalled()

    await userEvent.clear(amount)
    await userEvent.type(amount, '37.50')
    await userEvent.click(screen.getByRole('button', { name: 'Give $37.50' }))
    await waitFor(() => expect(mocks.start).toHaveBeenCalled())
    expect(mocks.start.mock.calls[0][0]).toMatchObject({ amount_cents: 3750 })
  })

  it('offers the display-name choice only to signed-in donors, off by default', async () => {
    const { unmount } = renderWithProviders(<DonationForm options={options} />)
    expect(screen.queryByLabelText(/Record this gift under my display name/)).not.toBeInTheDocument()
    unmount()
    renderWithProviders(<DonationForm options={options} />, { user: verifiedUser })
    const toggle = screen.getByLabelText(/Record this gift under my display name \(night_owl\)/)
    expect(toggle).not.toBeChecked()
    await userEvent.click(toggle)
    await userEvent.type(screen.getByLabelText(/Email for an acknowledgement/), 'owl@example.org')
    await userEvent.click(screen.getByRole('button', { name: 'Give $50' }))
    await waitFor(() => expect(mocks.start).toHaveBeenCalled())
    expect(mocks.start.mock.calls[0][0]).toMatchObject({ show_name: true, email: 'owl@example.org' })
  })
})

import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderWithProviders, verifiedUser } from '@/test/render'
import { AccountPage } from './AccountPage'

const api = vi.hoisted(() => ({ myRSVPs: vi.fn(), signOutEverywhere: vi.fn() }))
const membership = vi.hoisted(() => ({ me: vi.fn() }))
const feed = vi.hoisted(() => ({ get: vi.fn() }))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return { ...actual, api: { ...actual.api, ...api } }
})
vi.mock('@/lib/membershipApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membershipApi')>()
  return { ...actual, membershipApi: { ...actual.membershipApi, ...membership } }
})
vi.mock('@/lib/membersApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membersApi')>()
  return { ...actual, feedAccount: { ...actual.feedAccount, ...feed } }
})

beforeEach(() => {
  api.myRSVPs.mockResolvedValue([])
  api.signOutEverywhere.mockReset()
  membership.me.mockResolvedValue({ membership: null, entitlements: [] })
  feed.get.mockRejectedValue(new Error('not found'))
})

describe('AccountPage', () => {
  it('confirms before signing out everywhere', async () => {
    api.signOutEverywhere.mockResolvedValue({ user: null, csrfToken: 'fresh' })
    renderWithProviders(<AccountPage />, { user: verifiedUser, path: '/account' })
    await userEvent.click(await screen.findByRole('button', { name: 'Sign out everywhere' }))
    expect(api.signOutEverywhere).not.toHaveBeenCalled()
    const dialog = screen.getByRole('dialog', { name: 'Sign out everywhere?', hidden: true })
    expect(within(dialog).getByText(/including this one/)).toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    expect(api.signOutEverywhere).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: 'Sign out everywhere' }))
    await userEvent.click(within(dialog).getByRole('button', { name: 'Sign out everywhere' }))
    await waitFor(() => expect(api.signOutEverywhere).toHaveBeenCalledOnce())
  })
})

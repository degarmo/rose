import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/lib/api'
import type { FeedAccount } from '@/lib/membersApi'
import { renderWithProviders, verifiedUser } from '@/test/render'
import { FeedSection } from './FeedSection'

const api = vi.hoisted(() => ({ get: vi.fn(), stepAway: vi.fn(), erase: vi.fn(), requestExport: vi.fn() }))

vi.mock('@/lib/membersApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membersApi')>()
  return { ...actual, feedAccount: { ...actual.feedAccount, ...api } }
})

function account(overrides: Partial<FeedAccount> = {}): FeedAccount {
  return {
    participating: true,
    can_join: true,
    can_view: true,
    banned: false,
    suspended_until: null,
    accepted_current_guidelines: true,
    guidelines: null,
    has_content: true,
    profile: { display_name: 'night_owl', bio: '', hide_from_directory: true, has_avatar: false },
    export: null,
    ...overrides,
  }
}

const controls = { ...verifiedUser, feed_controls: true }

beforeEach(() => Object.values(api).forEach((fn) => fn.mockReset()))

describe('FeedSection', () => {
  it('asks for confirmation before stepping away', async () => {
    api.get.mockResolvedValue(account())
    api.stepAway.mockResolvedValue(account({ participating: false }))
    renderWithProviders(<FeedSection />, { user: controls })
    await userEvent.click(await screen.findByRole('button', { name: 'Step away from the feed' }))
    expect(api.stepAway).not.toHaveBeenCalled()
    const dialog = screen.getByRole('dialog', { name: 'Step away from the feed?', hidden: true })
    expect(within(dialog).getByText(/Nothing is deleted/)).toBeInTheDocument()

    await userEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    expect(api.stepAway).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: 'Step away from the feed' }))
    await userEvent.click(within(dialog).getByRole('button', { name: 'Step away' }))
    expect(api.stepAway).toHaveBeenCalledOnce()
    expect(await screen.findByRole('link', { name: 'Rejoin the feed' })).toHaveAttribute('href', '/members/join-feed')
  })

  it('only erases after the display name is typed exactly', async () => {
    api.get.mockResolvedValue(account())
    api.erase.mockResolvedValue(account({ participating: false, has_content: false }))
    renderWithProviders(<FeedSection />, { user: controls })
    await userEvent.click(await screen.findByRole('button', { name: 'Leave and erase' }))
    const dialog = screen.getByRole('dialog', { name: 'Erase everything you shared?', hidden: true })
    const confirm = within(dialog).getByRole('button', { name: 'Erase for good' })
    expect(confirm).toBeDisabled()
    await userEvent.type(within(dialog).getByLabelText('Display name'), 'Night_Owl')
    expect(confirm).toBeDisabled()
    await userEvent.clear(within(dialog).getByLabelText('Display name'))
    await userEvent.type(within(dialog).getByLabelText('Display name'), 'night_owl')
    await userEvent.click(confirm)
    await waitFor(() => expect(api.erase).toHaveBeenCalledWith('night_owl'))
    expect(await screen.findByText(/Erasing everything you shared/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Leave and erase' })).not.toBeInTheDocument()
  })

  it('explains that the community comes with membership when there is no access', async () => {
    api.get.mockRejectedValue(new ApiError(404, 'Not found.'))
    renderWithProviders(<FeedSection />, { user: controls })
    expect(await screen.findByRole('heading', { name: 'Member community' })).toBeInTheDocument()
    expect(screen.getByText(/comes with membership/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Join' })).toHaveAttribute('href', '/join')
    expect(screen.queryByRole('button', { name: 'Export my data' })).not.toBeInTheDocument()
  })

  it('does not ask the feed at all for someone without feed controls', async () => {
    renderWithProviders(<FeedSection />, { user: verifiedUser })
    expect(await screen.findByRole('heading', { name: 'Member community' })).toBeInTheDocument()
    expect(api.get).not.toHaveBeenCalled()
  })
})

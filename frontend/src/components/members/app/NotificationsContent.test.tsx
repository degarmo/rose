import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { FeedNotification } from '@/lib/membersApi'
import { renderInApp } from '@/test/members'
import { NotificationsContent } from './NotificationsContent'

const api = vi.hoisted(() => ({ notifications: vi.fn(), markNotificationsRead: vi.fn() }))

vi.mock('@/lib/membersApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membersApi')>()
  return { ...actual, members: { ...actual.members, ...api } }
})

const posted = { recent: true, at: new Date().toISOString(), month: null }

function note(overrides: Partial<FeedNotification>): FeedNotification {
  return { id: 1, kind: 'notice', text: '', post_id: null, thumbnail: null, actor: null, read: true, posted, ...overrides }
}

beforeEach(() => Object.values(api).forEach((fn) => fn.mockReset()))

describe('NotificationsContent', () => {
  it('opens Settings › Notices from a decision about the account, and the post from a post', async () => {
    api.notifications.mockResolvedValue({
      results: [
        note({ id: 1, text: 'A moderation decision about your account was recorded.' }),
        note({ id: 2, kind: 'like', text: '3 people liked your post.', post_id: 'p1' }),
        note({ id: 3, kind: 'guidelines', text: 'The guidelines were updated.' }),
      ],
    })
    renderInApp(<NotificationsContent />)
    expect(await screen.findByRole('link', { name: /moderation decision/ })).toHaveAttribute('href', '/members/settings/notices')
    expect(screen.getByRole('link', { name: /liked your post/ })).toHaveAttribute('href', '/members/p/p1')
    expect(screen.queryByRole('link', { name: /guidelines were updated/ })).not.toBeInTheDocument()
  })
})

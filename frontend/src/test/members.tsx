import type { ReactElement } from 'react'
import { vi } from 'vitest'
import type { Account } from '@/lib/api'
import type { FeedPost, Me } from '@/lib/membersApi'
import { MembersTestProvider } from './MembersTestProvider'
import { renderWithProviders, verifiedUser } from './render'

export const me: Me = {
  handle: 'night_owl',
  avatar: null,
  avatar_alt: '',
  bio: '',
  pronouns: '',
  hide_from_directory: false,
  always_show_sensitive: false,
  can_post: true,
  post_block_reason: null,
  unread_notifications: 0,
}

export function makePost(overrides: Partial<FeedPost> = {}): FeedPost {
  return {
    id: 'p1',
    author: { handle: 'velvet_hour', avatar: null },
    caption_html: 'Candles and quiet',
    caption: null,
    posted: { recent: true, at: new Date(Date.now() - 3600_000).toISOString(), month: null },
    edited: false,
    images: [
      { id: 'i1', url: '/api/members/media/i1/', alt: 'First', width: 1080, height: 1350 },
      { id: 'i2', url: '/api/members/media/i2/', alt: 'Second', width: 1080, height: 1350 },
    ],
    is_sensitive: false,
    blur: false,
    comments_enabled: true,
    comment_count: 0,
    liked_by_me: false,
    like_count: null,
    saved_by_me: false,
    recent_comments: [],
    is_own: false,
    state: null,
    in_review: null,
    ...overrides,
  }
}

export function renderInApp(ui: ReactElement, { user = { ...verifiedUser, feed_access: true } as Account, path = '/members/feed' } = {}) {
  const openPost = vi.fn()
  const result = renderWithProviders(<MembersTestProvider me={me} openPost={openPost}>{ui}</MembersTestProvider>, { user, path })
  return { ...result, openPost }
}

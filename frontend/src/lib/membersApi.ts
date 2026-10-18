import { postForBlob, postForm, post, request, send, type Page } from './api'

export interface MemberCard {
  handle: string
  avatar: string | null
}

/** Exact time for the last seven days; only the month after that. */
export interface Posted {
  recent: boolean
  at: string | null
  month: string | null
}

export interface FeedImage {
  id: string
  url: string
  alt: string
}

export type PostState = 'pending' | 'published' | 'hidden_by_report' | 'removed' | 'processing'

export interface FeedPost {
  id: string
  author: MemberCard
  caption_html: string
  caption: string | null
  posted: Posted
  edited: boolean
  images: FeedImage[]
  is_sensitive: boolean
  blur: boolean
  comments_enabled: boolean
  comment_count: number
  liked_by_me: boolean
  /** Only ever set for the post's author. */
  like_count: number | null
  is_own: boolean
  state: PostState | null
  /** Author only: waiting for a moderator before anyone else can see it. */
  in_review: boolean | null
}

export interface FeedComment {
  id: string
  author: MemberCard
  body_html: string
  posted: Posted
  can_delete: boolean
}

export interface MemberProfile {
  handle: string
  avatar: string | null
  bio: string
  joined: string
  is_self: boolean
  relationship: { following: boolean; muted: boolean } | null
}

export interface Me {
  handle: string
  avatar: string | null
  avatar_alt: string
  bio: string
  hide_from_directory: boolean
  always_show_sensitive: boolean
  can_post: boolean
  post_block_reason: 'guidelines' | 'cooldown' | null
  unread_notifications: number
}

export interface Guidelines {
  version: number
  title: string
  body: string
  body_html: string
  published_at: string
}

export interface FeedAccount {
  participating: boolean
  can_join: boolean
  can_view: boolean
  banned: boolean
  suspended_until: string | null
  accepted_current_guidelines: boolean
  guidelines: Guidelines | null
  has_content: boolean
  profile: { display_name: string; bio: string; hide_from_directory: boolean; has_avatar: boolean }
  export: { ready: boolean; expires_at: string | null } | null
}

export interface FeedNotification {
  id: number
  kind: 'like' | 'comment' | 'moderation' | 'guidelines'
  text: string
  post_id: string | null
  read: boolean
  posted: Posted
}

export type ReportReason = 'no_consent' | 'identifies' | 'harassment' | 'under_18' | 'spam' | 'other'
export type ReportTarget = 'post' | 'comment' | 'profile'
export type Relationship = 'follow' | 'block' | 'mute'

export interface NewPost {
  caption: string
  isSensitive: boolean
  commentsEnabled: boolean
  consentAttested: boolean
  /** Redacted, re-rendered images only. Originals never leave the device. */
  images: Array<{ blob: Blob; alt: string }>
}

function cursorFrom(url: string | null): string | null {
  if (!url) return null
  return new URL(url, window.location.origin).searchParams.get('cursor')
}

async function page(path: string, cursor: string | null) {
  const separator = path.includes('?') ? '&' : '?'
  const result = await request<Page<FeedPost>>(
    cursor ? `${path}${separator}cursor=${encodeURIComponent(cursor)}` : path,
  )
  return { items: result.results, nextCursor: cursorFrom(result.next) }
}

const enc = encodeURIComponent

export const members = {
  me: () => request<Me>('/members/me/'),
  updateMe: (changes: Partial<Pick<Me, 'bio' | 'hide_from_directory' | 'always_show_sensitive'>>) =>
    send<Me>('PATCH', '/members/me/', changes),
  uploadAvatar: (blob: Blob, alt: string, showsFace: boolean, attested: boolean) => {
    const form = new FormData()
    form.append('image', blob, 'avatar.jpg')
    form.append('alt', alt)
    form.append('shows_face', String(showsFace))
    form.append('consent_attested', String(attested))
    return postForm<Me>('/members/me/avatar/', form)
  },
  removeAvatar: () => send<Me>('DELETE', '/members/me/avatar/'),
  myBlocks: () => request<{ blocked: string[] }>('/members/me/blocks/'),
  guidelines: () => request<Guidelines>('/members/guidelines/'),

  feed: (tab: 'everyone' | 'following', cursor: string | null = null) =>
    page(`/members/feed/?tab=${tab}`, cursor),
  memberPosts: (handle: string, cursor: string | null = null) =>
    page(`/members/u/${enc(handle)}/posts/`, cursor),
  post: (id: string) => request<FeedPost>(`/members/posts/${enc(id)}/`),
  createPost: (draft: NewPost) => {
    const form = new FormData()
    form.append('caption', draft.caption)
    form.append('is_sensitive', String(draft.isSensitive))
    form.append('comments_enabled', String(draft.commentsEnabled))
    form.append('consent_attested', String(draft.consentAttested))
    draft.images.forEach((image, index) => {
      form.append('images', image.blob, `image-${index + 1}.jpg`)
      form.append('alt', image.alt)
    })
    return postForm<FeedPost>('/members/feed/', form)
  },
  editPost: (id: string, changes: { caption?: string; is_sensitive?: boolean; comments_enabled?: boolean }) =>
    send<FeedPost>('PATCH', `/members/posts/${enc(id)}/`, changes),
  deletePost: (id: string) => send<null>('DELETE', `/members/posts/${enc(id)}/`),
  like: (id: string) => post<FeedPost>(`/members/posts/${enc(id)}/like/`),
  unlike: (id: string) => send<FeedPost>('DELETE', `/members/posts/${enc(id)}/like/`),
  comments: (id: string) => request<FeedComment[]>(`/members/posts/${enc(id)}/comments/`),
  addComment: (id: string, body: string) => post<FeedComment>(`/members/posts/${enc(id)}/comments/`, { body }),
  deleteComment: (id: string) => send<null>('DELETE', `/members/comments/${enc(id)}/`),

  profile: (handle: string) => request<MemberProfile>(`/members/u/${enc(handle)}/`),
  relate: (handle: string, kind: Relationship) => post<{ ok: true }>(`/members/u/${enc(handle)}/${kind}/`),
  unrelate: (handle: string, kind: Relationship) =>
    send<{ ok: true }>('DELETE', `/members/u/${enc(handle)}/${kind}/`),
  directory: (query: string) =>
    request<{ results: MemberCard[]; min_query: number }>(`/members/directory/?q=${enc(query)}`),
  notifications: () => request<{ results: FeedNotification[] }>('/members/notifications/'),
  markNotificationsRead: () => post<{ ok: true }>('/members/notifications/read/'),
  report: (targetType: ReportTarget, targetId: string, reason: ReportReason, details: string) =>
    post<{ detail: string }>('/members/reports/', {
      target_type: targetType,
      target_id: targetId,
      reason,
      details,
    }),
}

export const feedAccount = {
  get: () => request<FeedAccount>('/account/feed/'),
  join: (guidelinesVersion: number, bio: string, hideFromDirectory: boolean) =>
    post<FeedAccount>('/account/feed/join/', {
      guidelines_version: guidelinesVersion,
      bio,
      hide_from_directory: hideFromDirectory,
    }),
  acceptGuidelines: (guidelinesVersion: number) =>
    post<FeedAccount>('/account/feed/guidelines/', { guidelines_version: guidelinesVersion }),
  stepAway: () => post<FeedAccount>('/account/feed/step-away/'),
  erase: (displayName: string) => post<FeedAccount>('/account/feed/erase/', { display_name: displayName }),
  requestExport: () => post<FeedAccount>('/account/feed/export/'),
  downloadExport: (token: string) => postForBlob('/account/feed/export/download/', { token }),
}

export const REPORT_REASONS: Array<{ value: ReportReason; label: string }> = [
  { value: 'no_consent', label: 'Posted without consent' },
  { value: 'identifies', label: 'Identifies someone' },
  { value: 'harassment', label: 'Harassment' },
  { value: 'under_18', label: 'May involve someone under 18' },
  { value: 'spam', label: 'Spam' },
  { value: 'other', label: 'Something else' },
]

const monthFormatter = new Intl.DateTimeFormat('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' })

/** "Mar 2026" for anything older than a week; relative time otherwise. */
export function postedLabel(posted: Posted, relative: (iso: string) => string): string {
  if (posted.recent && posted.at) return relative(posted.at)
  if (posted.month) {
    const [year, month] = posted.month.split('-').map(Number)
    return monthFormatter.format(new Date(Date.UTC(year, month - 1, 1)))
  }
  return ''
}

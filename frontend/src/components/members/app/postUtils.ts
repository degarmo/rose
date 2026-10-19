import type { ClubPost, FeedImage, FeedPost } from '@/lib/membersApi'

export function isClub(post: FeedPost | ClubPost): post is ClubPost {
  return 'kind' in post && post.kind === 'club'
}

export function profilePath(handle: string) {
  return `/members/u/${encodeURIComponent(handle)}`
}

// Taller than 4:5 or wider than 1.91:1 is cropped to those limits.
const MIN_RATIO = 4 / 5
const MAX_RATIO = 1.91

/** Width over height for the whole post, from its first image, clamped. Square when unknown. */
export function mediaRatio(images: FeedImage[]): number {
  const first = images[0]
  if (!first?.width || !first.height) return 1
  return Math.min(Math.max(first.width / first.height, MIN_RATIO), MAX_RATIO)
}

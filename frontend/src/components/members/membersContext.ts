import { createContext, useContext } from 'react'
import type { FeedPost, Me } from '@/lib/membersApi'

export interface MembersState {
  me: Me
  refreshMe: () => Promise<void>
  setMe: (me: Me) => void
  /** Bumped after a new post, so lists can reload. */
  postsVersion: number
  /**
   * Open a post: a modal over the current page on tablets and desktops, its own page on
   * phones. `listIds` lets the modal step through the list with the arrow keys.
   */
  openPost: (id: string, listIds?: string[]) => void
  /**
   * The latest copy of every post changed in this session (liked, saved, edited,
   * commented on), or null once deleted or hidden, so every list and the post view agree.
   */
  postUpdates: ReadonlyMap<string, FeedPost | null>
  updatePost: (id: string, post: FeedPost | null) => void
  /**
   * Change a post starting from its newest copy (or `base` if it has not changed yet), so
   * replies that arrive late, like a like's, never undo a newer change such as a comment.
   */
  patchPost: (base: FeedPost, change: (current: FeedPost) => FeedPost) => void
}

export const MembersContext = createContext<MembersState | null>(null)

export function useMembers(): MembersState {
  const context = useContext(MembersContext)
  if (!context) throw new Error('useMembers must be used inside the members area')
  return context
}

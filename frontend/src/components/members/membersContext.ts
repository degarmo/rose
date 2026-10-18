import { createContext, useContext } from 'react'
import type { Me } from '@/lib/membersApi'

export interface MembersState {
  me: Me
  refreshMe: () => Promise<void>
  setMe: (me: Me) => void
  openComposer: () => void
  /** Bumped after a new post, so lists can reload. */
  postsVersion: number
  notePosted: () => void
}

export const MembersContext = createContext<MembersState | null>(null)

export function useMembers(): MembersState {
  const context = useContext(MembersContext)
  if (!context) throw new Error('useMembers must be used inside the members area')
  return context
}

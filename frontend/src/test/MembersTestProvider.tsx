import { useMemo, useState, type ReactNode } from 'react'
import { MembersContext, type MembersState } from '@/components/members/membersContext'
import type { FeedPost, Me } from '@/lib/membersApi'

/** The member app's context with real post updates, so a like shows up as it would in the app. */
export function MembersTestProvider({ children, me, openPost }: { children: ReactNode; me: Me; openPost: MembersState['openPost'] }) {
  const [postUpdates, setPostUpdates] = useState<ReadonlyMap<string, FeedPost | null>>(new Map())
  const value = useMemo<MembersState>(
    () => ({
      me,
      refreshMe: async () => undefined,
      setMe: () => undefined,
      postsVersion: 0,
      openPost,
      postUpdates,
      updatePost: (id, post) => setPostUpdates((current) => new Map(current).set(id, post)),
      patchPost: (base, change) =>
        setPostUpdates((current) => {
          const latest = current.has(base.id) ? current.get(base.id) : base
          return latest ? new Map(current).set(base.id, change(latest)) : current
        }),
    }),
    [me, openPost, postUpdates],
  )
  return <MembersContext.Provider value={value}>{children}</MembersContext.Provider>
}

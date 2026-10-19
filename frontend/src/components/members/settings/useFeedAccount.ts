import { useState } from 'react'
import { useAuth } from '@/components/layout/authContext'
import { useToast } from '@/components/ui'
import { feedAccount, type FeedAccount } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'

/**
 * The feed controls (join, step away, erase), fetched only for people who have them, so
 * nobody else's Settings asks the feed for a 404. `account` is null for everyone else.
 */
export function useFeedAccount() {
  const auth = useAuth()
  const toast = useToast()
  const controls = Boolean(auth.user?.feed_controls)
  const state = useAsync(() => (controls ? feedAccount.get() : Promise.resolve(null)), `account-feed:${controls}`)
  const [local, setLocal] = useState<FeedAccount | null>(null)
  const [busy, setBusy] = useState(false)
  const account = local ?? (state.status === 'success' ? state.data : null)

  async function act(action: () => Promise<FeedAccount>, success: string): Promise<boolean> {
    setBusy(true)
    try {
      setLocal(await action())
      toast.show({ tone: 'success', title: success })
      await auth.refresh()
      return true
    } catch (error) {
      toast.show({
        tone: 'error',
        title: 'That did not work',
        message: error instanceof Error ? error.message : undefined,
      })
      return false
    } finally {
      setBusy(false)
    }
  }

  return { controls, state, account, busy, act }
}

import { ArrowRight } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '@/components/layout/authContext'
import { ConfirmDialog } from '@/components/members/ConfirmDialog'
import { PaywallPanel } from '@/components/membership/PaywallPanel'
import { Button, ButtonLink, Card, FormField, Input, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { formatEventDate } from '@/lib/format'
import { feedAccount, type FeedAccount } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'

type Dialog = 'step-away' | 'erase' | null

function FeedPaywall() {
  return (
    <PaywallPanel
      title="Member community"
      benefit="The member feed, a private space to share with other members, comes with membership. It stays off until you turn it on."
    />
  )
}

/**
 * Feed controls, or an explanation that the feed comes with membership. The controls are
 * fetched only for people who have them, so nobody else's page asks the feed for a 404.
 */
export function FeedSection() {
  const auth = useAuth()
  return auth.user?.feed_controls ? <FeedControls /> : <FeedPaywall />
}

function FeedControls() {
  const auth = useAuth()
  const toast = useToast()
  const state = useAsync(() => feedAccount.get(), 'account-feed')
  const [override, setOverride] = useState<FeedAccount | null>(null)
  const [dialog, setDialog] = useState<Dialog>(null)
  const [confirmName, setConfirmName] = useState('')
  const [busy, setBusy] = useState(false)
  const [erasing, setErasing] = useState(false)

  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) return <FeedPaywall />
  if (state.status !== 'success') return null
  const account = override ?? state.data
  const handle = auth.user?.display_name ?? ''
  const showData = account.has_content && !erasing

  async function act(action: () => Promise<FeedAccount>, success: string): Promise<boolean> {
    setBusy(true)
    try {
      setOverride(await action())
      setDialog(null)
      toast.show({ tone: 'success', title: success })
      return true
    } catch (error) {
      toast.show({ tone: 'error', title: 'That did not work', message: error instanceof Error ? error.message : undefined })
      return false
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card as="article" aria-labelledby="feed-heading" className="p-6 sm:p-8">
      <h2 id="feed-heading" className="text-3xl text-fg">
        Member feed
      </h2>
      <div className="mt-6 flex flex-col gap-6 text-fg-muted">
        {account.banned && <p>Your access to the member feed has been withdrawn. You can still download or erase what you shared.</p>}
        {account.suspended_until && <p>Your feed access is paused until {formatEventDate(account.suspended_until)}.</p>}

        {account.participating && !account.banned && (
          <div className="flex flex-col gap-4">
            <p>You are part of the member feed.</p>
            <div className="flex flex-wrap gap-3">
              <ButtonLink to="/members/feed">
                Open the feed
                <ArrowRight aria-hidden="true" className="size-4" />
              </ButtonLink>
              <Button variant="ghost" onClick={() => setDialog('step-away')}>
                Step away from the feed
              </Button>
            </div>
          </div>
        )}
        {!account.participating && account.can_join && !erasing && (
          <div className="flex flex-col gap-3">
            <p>{account.has_content ? 'You stepped away. Rejoin and everything you shared comes back.' : 'A private space to share with other members. Off unless you turn it on.'}</p>
            <ButtonLink to="/members/join-feed" className="self-start">
              {account.has_content ? 'Rejoin the feed' : 'Join the member feed'}
            </ButtonLink>
          </div>
        )}

        {erasing && (
          <p role="status" className="border-t border-border pt-6 text-sm">
            Erasing everything you shared. We will email you when it is done.
          </p>
        )}

        {showData && (
          <div className="flex flex-col gap-3 border-t border-border pt-6">
            <h3 className="font-display text-xl text-fg">Your data</h3>
            <p className="text-sm">Get a zip of your profile, posts, comments, likes and photos. We email a link that works once, for 24 hours.</p>
            {account.export && !account.export.ready && <p className="text-sm text-highlight">Your copy is being prepared. Watch your inbox.</p>}
            <Button variant="ghost" className="self-start" disabled={busy || Boolean(account.export && !account.export.ready)} onClick={() => void act(feedAccount.requestExport, 'We will email you a link shortly')}>
              Export my data
            </Button>
          </div>
        )}

        {showData && (
          <div className="flex flex-col gap-3 border-t border-border pt-6">
            <h3 className="font-display text-xl text-fg">Leave and erase</h3>
            <p className="text-sm">Permanently deletes your posts, photos, comments, likes, follows, blocks and notifications. Your account stays.</p>
            <Button variant="ghost" className="self-start border-danger/60 text-danger" onClick={() => setDialog('erase')}>
              Leave and erase
            </Button>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={dialog === 'step-away'}
        title="Step away from the feed?"
        confirmLabel="Step away"
        busy={busy}
        onClose={() => setDialog(null)}
        onConfirm={() => void act(feedAccount.stepAway, 'You have stepped away')}
      >
        <p>Everything you posted, commented on or liked disappears for everyone straight away, along with your picture and bio.</p>
        <p>Nothing is deleted. Rejoin any time and it all comes back.</p>
      </ConfirmDialog>
      <ConfirmDialog
        open={dialog === 'erase'}
        title="Erase everything you shared?"
        confirmLabel="Erase for good"
        busy={busy}
        disabled={confirmName !== handle}
        onClose={() => {
          setDialog(null)
          setConfirmName('')
        }}
        onConfirm={() =>
          void act(() => feedAccount.erase(confirmName), 'Erasing now. We will email you when it is done.').then((ok) => {
            if (!ok) return
            setErasing(true)
            setConfirmName('')
          })
        }
      >
        <p>This cannot be undone. Type your display name, <strong className="text-fg">{handle}</strong>, to confirm.</p>
        <FormField label="Display name" optionalLabel="">
          {(field) => <Input {...field} autoComplete="off" spellCheck={false} value={confirmName} onChange={(e) => setConfirmName(e.target.value)} />}
        </FormField>
      </ConfirmDialog>
    </Card>
  )
}

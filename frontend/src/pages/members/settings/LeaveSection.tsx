import { Check, Pause, Trash2, X } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { ConfirmDialog } from '@/components/members/ConfirmDialog'
import { AppButton } from '@/components/members/app/primitives'
import { Card, LinkRow, Skeleton } from '@/components/members/settings/ui'
import { useFeedAccount } from '@/components/members/settings/useFeedAccount'
import { FormField, Input } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import { feedAccount } from '@/lib/membersApi'

function What({ removed, kept }: { removed: string[]; kept: string[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted">Removed</p>
        <ul className="mt-2 flex flex-col gap-1.5">
          {removed.map((item) => (
            <li key={item} className="flex gap-2 text-fg">
              <X aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-danger" />
              {item}
            </li>
          ))}
        </ul>
      </div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted">Kept</p>
        <ul className="mt-2 flex flex-col gap-1.5">
          {kept.map((item) => (
            <li key={item} className="flex gap-2 text-fg">
              <Check aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-fg-muted" />
              {item}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

const dangerButton = 'self-start bg-transparent text-danger ring-1 ring-danger hover:bg-surface'

/** Leave the member community and erase everything you shared there, for good. */
function LeaveAndErase() {
  const auth = useAuth()
  const feed = useFeedAccount()
  const [erasing, setErasing] = useState(false)
  const [open, setOpen] = useState(false)
  const [confirmName, setConfirmName] = useState('')
  const handle = auth.user?.display_name ?? ''
  const account = feed.account
  if (feed.controls && !account) return <Skeleton lines={3} />
  if (erasing) {
    return (
      <p role="status" className="rounded-app bg-surface p-4 text-fg">
        Erasing everything you shared. We will email you when it is done.
      </p>
    )
  }
  if (!account?.has_content) return <p className="text-fg-muted">You have not shared anything in the member feed, so there is nothing to erase.</p>

  return (
    <div className="flex flex-col gap-4">
      <p className="text-fg">Leave the member community and delete everything you shared in it. Your account and membership stay.</p>
      <What
        removed={[
          'Your posts and their photos',
          'Your comments and likes',
          'Saved posts, follows, blocks and mutes',
          'Your notifications',
          'Your picture and bio',
        ]}
        kept={['Your account and sign-in', 'Your membership and payments', 'Your RSVPs', 'Reports you sent, and our team’s records']}
      />
      <p className="text-meta text-fg-muted">This cannot be undone. We email you when it is done.</p>
      <AppButton variant="plain" className={dangerButton} onClick={() => setOpen(true)}>
        <Trash2 aria-hidden="true" className="size-4" />
        Leave and erase
      </AppButton>
      <ConfirmDialog
        open={open}
        title="Erase everything you shared?"
        confirmLabel="Erase for good"
        busy={feed.busy}
        disabled={confirmName !== handle}
        onClose={() => {
          setOpen(false)
          setConfirmName('')
        }}
        onConfirm={() =>
          void feed
            .act(() => feedAccount.erase(confirmName), 'Erasing now. We will email you when it is done.')
            .then((ok) => {
              if (!ok) return
              setOpen(false)
              setConfirmName('')
              // The refreshed session closes the feed; this screen stays, with the status in view.
              setErasing(true)
            })
        }
      >
        <p>
          This cannot be undone. Type your display name, <strong className="text-fg">{handle}</strong>, to confirm.
        </p>
        <FormField label="Display name" optionalLabel="">
          {(field) => <Input {...field} autoComplete="off" spellCheck={false} value={confirmName} onChange={(e) => setConfirmName(e.target.value)} />}
        </FormField>
      </ConfirmDialog>
    </div>
  )
}

/** Delete the whole account. Needs the password. */
function DeleteAccount() {
  const auth = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)

  async function confirm() {
    if (!password) return setError('Enter your password to confirm.')
    setBusy(true)
    try {
      auth.applySession(await api.deleteAccount(password))
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError && err.fieldErrors.password ? err.fieldErrors.password : 'Please try again.')
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-fg">Delete your account and everything tied to it, straight away.</p>
      <What
        removed={[
          'Your profile and sign-in',
          'Every RSVP (your places go to the waitlist)',
          'Everything you shared in the member feed',
          'An open membership is cancelled',
        ]}
        kept={['Messages you sent us, without your name, email or phone', 'Payment records for our accounts, with nothing that identifies you']}
      />
      <p className="text-meta text-fg-muted">This cannot be undone.</p>
      <AppButton variant="plain" className={dangerButton} onClick={() => setOpen(true)}>
        <Trash2 aria-hidden="true" className="size-4" />
        Delete my account
      </AppButton>
      <ConfirmDialog
        open={open}
        title="Delete your account?"
        confirmLabel="Delete for good"
        busy={busy}
        onClose={() => {
          setOpen(false)
          setPassword('')
          setError(undefined)
        }}
        onConfirm={() => void confirm()}
      >
        <p>Your RSVPs will be released to the waitlist. Enter your password to confirm.</p>
        <FormField label="Password" error={error} required>
          {(field) => (
            <Input
              {...field}
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value)
                setError(undefined)
              }}
            />
          )}
        </FormField>
      </ConfirmDialog>
    </div>
  )
}

/** Settings · Leave the community: a break, erasing what you shared, or deleting the account. */
export function LeaveSection() {
  const auth = useAuth()
  return (
    <div className="flex flex-col gap-4">
      {auth.user?.member_app === 'open' && (
        <Card>
          <ul>
            <LinkRow icon={Pause} label="Just need a break?" sub="Step away from the feed instead: nothing is deleted" to="/members/settings/privacy" />
          </ul>
        </Card>
      )}
      <Card title="Leave the community">
        <LeaveAndErase />
      </Card>
      <Card title="Delete your account">
        <DeleteAccount />
      </Card>
    </div>
  )
}

import { ChevronRight, ExternalLink } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { ConfirmDialog } from '@/components/members/ConfirmDialog'
import { useMembers } from '@/components/members/membersContext'
import { BlockedList, EditProfileDialog } from '@/components/members/ProfileSettings'
import { Toggle } from '@/components/members/Toggle'
import { FormField, Input, useToast } from '@/components/ui'
import type { Appearance } from '@/lib/api'
import { chooseAppearance } from '@/lib/appearance'
import { cn } from '@/lib/cn'
import { feedAccount, members } from '@/lib/membersApi'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section aria-label={title} className="border-b border-border py-4 last:border-b-0">
      <h2 className="px-4 pb-2 text-base font-semibold text-fg">{title}</h2>
      <div className="flex flex-col">{children}</div>
    </section>
  )
}

const row = 'flex min-h-12 w-full items-center gap-3 rounded-lg px-4 text-left hover:bg-surface'

/** Everything about how you appear and what the app does with your data, as one list. */
export function SettingsPage() {
  useDocumentMeta({ title: 'Settings', noindex: true })
  const auth = useAuth()
  const navigate = useNavigate()
  const toast = useToast()
  const { me, setMe } = useMembers()
  const [dialog, setDialog] = useState<'edit' | 'step-away' | 'erase' | null>(null)
  const [busy, setBusy] = useState(false)
  const [exportAsked, setExportAsked] = useState(false)
  const [confirmName, setConfirmName] = useState('')
  const appearance: Appearance = auth.user?.appearance ?? 'light'

  async function update(changes: Parameters<typeof members.updateMe>[0]) {
    setBusy(true)
    try {
      setMe(await members.updateMe(changes))
    } catch {
      toast.show({ tone: 'error', title: 'Your change was not saved' })
    } finally {
      setBusy(false)
    }
  }

  async function setAppearance(next: Appearance) {
    const session = await chooseAppearance(next, Boolean(auth.user))
    if (session) auth.applySession(session)
  }

  async function act(action: () => Promise<unknown>, success: string, then: () => void) {
    setBusy(true)
    try {
      await action()
      setDialog(null)
      toast.show({ tone: 'success', title: success })
      then()
    } catch (error) {
      toast.show({ tone: 'error', title: 'That did not work', message: error instanceof Error ? error.message : undefined })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-[600px] pb-10 pt-4 md:pt-8">
      <h1 className="px-4 pb-2 text-base font-semibold text-fg md:text-2xl">Settings</h1>

      <Group title="Your profile">
        <button type="button" className={row} onClick={() => setDialog('edit')}>
          <span className="flex-1">Edit profile</span>
          <ChevronRight aria-hidden="true" className="size-4 text-fg-muted" />
        </button>
      </Group>

      <Group title="Appearance">
        <div role="radiogroup" aria-label="Appearance" className="flex gap-2 px-4 py-2">
          {(['light', 'dark'] as const).map((value) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={appearance === value}
              onClick={() => void setAppearance(value)}
              className={cn(
                'h-8 flex-1 rounded-lg border text-sm font-semibold transition-colors duration-150',
                appearance === value ? 'border-fg bg-fg text-canvas' : 'border-border text-fg hover:bg-surface',
              )}
            >
              {value === 'light' ? 'Light' : 'Dark'}
            </button>
          ))}
        </div>
        <p className="px-4 text-xs text-fg-muted">Applies to the website too, on every device you sign in on.</p>
      </Group>

      <Group title="What you see">
        <div className="px-4 py-2">
          <Toggle
            label="Always show sensitive posts"
            hint="Skip the blur on posts marked sensitive."
            checked={me.always_show_sensitive}
            disabled={busy}
            onChange={(value) => void update({ always_show_sensitive: value })}
          />
        </div>
      </Group>

      <Group title="Who can find you">
        <div className="px-4 py-2">
          <Toggle
            label="Show me in search"
            hint="When off, people can only find you through your posts and comments."
            checked={!me.hide_from_directory}
            disabled={busy}
            onChange={(value) => void update({ hide_from_directory: !value })}
          />
        </div>
      </Group>

      <Group title="Blocked">
        <div className="px-4 py-2">
          <BlockedList />
        </div>
      </Group>

      <Group title="Your data">
        <button type="button" className={row} onClick={() => setDialog('step-away')}>
          <span className="flex-1">Step away from the feed</span>
          <ChevronRight aria-hidden="true" className="size-4 text-fg-muted" />
        </button>
        <button
          type="button"
          className={row}
          disabled={busy || exportAsked}
          onClick={() => void act(feedAccount.requestExport, 'We will email you a link shortly', () => setExportAsked(true))}
        >
          <span className="flex-1">
            Export my data
            <span className="block text-xs text-fg-muted">
              {exportAsked ? 'Your copy is being prepared. Watch your inbox.' : 'A zip of your profile, posts, comments, likes, saved posts and photos.'}
            </span>
          </span>
        </button>
        <button type="button" className={cn(row, 'text-danger')} onClick={() => setDialog('erase')}>
          <span className="flex-1 font-semibold">Leave and erase</span>
        </button>
      </Group>

      <Group title="Account">
        <Link to="/account" className={row}>
          <span className="flex-1">Your account on the website</span>
          <ExternalLink aria-hidden="true" className="size-4 text-fg-muted" />
        </Link>
      </Group>

      <EditProfileDialog open={dialog === 'edit'} onClose={() => setDialog(null)} />
      <ConfirmDialog
        open={dialog === 'step-away'}
        title="Step away from the feed?"
        confirmLabel="Step away"
        busy={busy}
        onClose={() => setDialog(null)}
        onConfirm={() => void act(feedAccount.stepAway, 'You have stepped away', () => navigate('/account', { replace: true }))}
      >
        <p>Everything you posted, commented on or liked disappears for everyone straight away, along with your picture and bio.</p>
        <p>Nothing is deleted. Rejoin any time and it all comes back.</p>
      </ConfirmDialog>
      <ConfirmDialog
        open={dialog === 'erase'}
        title="Erase everything you shared?"
        confirmLabel="Erase for good"
        busy={busy}
        disabled={confirmName !== me.handle}
        onClose={() => {
          setDialog(null)
          setConfirmName('')
        }}
        onConfirm={() =>
          void act(() => feedAccount.erase(confirmName), 'Erasing now. We will email you when it is done.', () => navigate('/account', { replace: true }))
        }
      >
        <p>
          Permanently deletes your posts, photos, comments, likes, saved posts, follows, blocks and notifications. Your account stays. This
          cannot be undone. Type your display name, <strong className="text-fg">{me.handle}</strong>, to confirm.
        </p>
        <FormField label="Display name" optionalLabel="">
          {(field) => <Input {...field} autoComplete="off" spellCheck={false} value={confirmName} onChange={(e) => setConfirmName(e.target.value)} />}
        </FormField>
      </ConfirmDialog>
    </div>
  )
}

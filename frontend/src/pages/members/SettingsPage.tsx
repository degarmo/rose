import { Ban, Check, ChevronRight, Download, EyeOff, Pause, Search, Sun, Trash2, User, UserCog, type LucideIcon } from 'lucide-react'
import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { PhoneBar } from '@/components/members/app/Nav'
import { ICON } from '@/components/members/app/ui'
import { ConfirmDialog } from '@/components/members/ConfirmDialog'
import { useMembers } from '@/components/members/membersContext'
import { BlockedList, EditProfileDialog } from '@/components/members/ProfileSettings'
import { FormField, Input, Switch, useToast } from '@/components/ui'
import type { Appearance } from '@/lib/api'
import { chooseAppearance } from '@/lib/appearance'
import { cn } from '@/lib/cn'
import { feedAccount, members } from '@/lib/membersApi'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/** One settings row (design: 56px, a 24px icon, the label at 600 over an optional 12px line). */
const settingsRow = 'flex min-h-14 w-full items-center gap-4 border-b border-border py-2 text-left'

function RowText({ label, sub, danger = false }: { label: ReactNode; sub?: ReactNode; danger?: boolean }) {
  return (
    <span className="min-w-0 flex-1">
      <span className={cn('block font-semibold', danger ? 'text-danger' : 'text-fg')}>{label}</span>
      {sub && <span className="block text-meta text-fg-muted">{sub}</span>}
    </span>
  )
}

function RowIcon({ icon: Icon, danger = false }: { icon: LucideIcon; danger?: boolean }) {
  return <Icon aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} className={cn('shrink-0', danger ? 'text-danger' : 'text-fg')} />
}

const chevron = <ChevronRight aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} className="shrink-0 text-fg-muted" />

/** A row that opens something: icon, label, an optional value, then a chevron. */
function ActionRowButton({ icon, label, sub, value, danger, onClick, disabled }: { icon: LucideIcon; label: string; sub?: ReactNode; value?: string; danger?: boolean; onClick: () => void; disabled?: boolean }) {
  return (
    <li>
      <button type="button" className={cn(settingsRow, 'hover:bg-surface disabled:cursor-default disabled:hover:bg-transparent')} onClick={onClick} disabled={disabled}>
        <RowIcon icon={icon} danger={danger} />
        <RowText label={label} sub={sub} danger={danger} />
        {value && <span className="shrink-0 text-fg-muted">{value}</span>}
        {chevron}
      </button>
    </li>
  )
}

/** A row with a switch on the right; the words are its label. */
function SwitchRow({ icon, label, sub, checked, disabled, onChange }: { icon: LucideIcon; label: string; sub: string; checked: boolean; disabled: boolean; onChange: (value: boolean) => void }) {
  const id = useId()
  return (
    <li className={settingsRow}>
      <RowIcon icon={icon} />
      <label htmlFor={id} className="min-w-0 flex-1 cursor-pointer">
        <RowText label={label} sub={sub} />
      </label>
      <Switch id={id} checked={checked} disabled={disabled} onChange={onChange} />
    </li>
  )
}

/** A small sheet with Light and Dark, the current one ticked; choosing applies at once. */
function AppearanceChooser({ open, value, onClose, onChoose }: { open: boolean; value: Appearance; onClose: () => void; onChoose: (value: Appearance) => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])
  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === ref.current) onClose()
      }}
      className="m-0 h-dvh max-h-none w-screen max-w-none items-center justify-center bg-transparent p-4 open:flex"
    >
      <div className="w-full max-w-[400px] overflow-hidden rounded-sheet bg-canvas text-fg shadow-sheet">
        <h2 id={titleId} className="flex h-12 items-center justify-center border-b border-border font-semibold">
          Appearance
        </h2>
        <div role="radiogroup" aria-labelledby={titleId} className="divide-y divide-border">
          {(['light', 'dark'] as const).map((option) => (
            <button
              key={option}
              type="button"
              role="radio"
              aria-checked={value === option}
              onClick={() => onChoose(option)}
              className="flex min-h-12 w-full items-center gap-3 px-4 text-left hover:bg-surface"
            >
              <span className="flex-1">{option === 'light' ? 'Light' : 'Dark'}</span>
              {value === option && <Check aria-hidden="true" size={20} strokeWidth={ICON.stroke} className="text-link" />}
            </button>
          ))}
        </div>
        <p className="border-t border-border px-4 py-3 text-meta text-fg-muted">Applies to the website too, on every device you sign in on.</p>
        <button type="button" onClick={onClose} className="flex min-h-12 w-full items-center justify-center border-t border-border hover:bg-surface">
          Cancel
        </button>
      </div>
    </dialog>
  )
}

/** Settings (design: "Settings"): one list of 56px rows, then your blocks and the website account. */
export function SettingsPage() {
  useDocumentMeta({ title: 'Settings', noindex: true })
  const auth = useAuth()
  const navigate = useNavigate()
  const toast = useToast()
  const { me, setMe } = useMembers()
  const [dialog, setDialog] = useState<'edit' | 'appearance' | 'step-away' | 'erase' | null>(null)
  const blockedId = useId()
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
    <>
      <PhoneBar back title={<h1 className="truncate text-base font-semibold">Settings</h1>} />
      <div className="mx-auto w-full max-w-[632px] px-4 pb-10 md:pt-10">
        <h1 className="hidden pb-6 text-xl font-semibold text-fg md:block">Settings</h1>
        <ul>
          <ActionRowButton icon={User} label="Edit profile" onClick={() => setDialog('edit')} />
          <ActionRowButton icon={Sun} label="Appearance" value={appearance === 'dark' ? 'Dark' : 'Light'} onClick={() => setDialog('appearance')} />
          <SwitchRow
            icon={EyeOff}
            label="Always show sensitive posts"
            sub="Skip the blur and View step"
            checked={me.always_show_sensitive}
            disabled={busy}
            onChange={(value) => void update({ always_show_sensitive: value })}
          />
          <SwitchRow
            icon={Search}
            label="Hide me from the member directory"
            sub="You can still post and comment"
            checked={me.hide_from_directory}
            disabled={busy}
            onChange={(value) => void update({ hide_from_directory: value })}
          />
          <ActionRowButton icon={Pause} label="Step away from the feed" sub="Pause your feed profile for a while" onClick={() => setDialog('step-away')} />
          <ActionRowButton
            icon={Download}
            label="Export my data"
            sub={exportAsked ? 'Your copy is being prepared. Watch your inbox.' : undefined}
            disabled={busy || exportAsked}
            onClick={() => void act(feedAccount.requestExport, 'We will email you a link shortly', () => setExportAsked(true))}
          />
          <ActionRowButton icon={Trash2} label="Leave and erase" sub="Permanently delete everything you shared" danger onClick={() => setDialog('erase')} />
        </ul>
        <section aria-labelledby={blockedId}>
          <div className={settingsRow}>
            <RowIcon icon={Ban} />
            <RowText label={<span id={blockedId}>Blocked</span>} sub="They are not told, and you can unblock any time" />
          </div>
          <BlockedList />
        </section>
        <ul>
          <li>
            <Link to="/account" className={cn(settingsRow, 'hover:bg-surface')}>
              <RowIcon icon={UserCog} />
              <RowText label="Your account on the website" />
              {chevron}
            </Link>
          </li>
        </ul>
      </div>

      <AppearanceChooser
        open={dialog === 'appearance'}
        value={appearance}
        onClose={() => setDialog((d) => (d === 'appearance' ? null : d))}
        onChoose={(next) => {
          setDialog(null)
          void setAppearance(next)
        }}
      />
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
    </>
  )
}

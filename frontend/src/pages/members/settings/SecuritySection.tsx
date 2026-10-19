import { Copy, EyeOff, LogOut, Mail, MonitorSmartphone, ShieldCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { ConfirmDialog } from '@/components/members/ConfirmDialog'
import { AppButton } from '@/components/members/app/primitives'
import { ICON } from '@/components/members/app/ui'
import { Card, LoadError, RowIcon, RowText, Skeleton, StatusChip } from '@/components/members/settings/ui'
import { FormField, Input, Modal, useToast } from '@/components/ui'
import { api, ApiError, type TwoStepState } from '@/lib/api'
import { formatDay, relativeDate } from '@/lib/format'
import { useAsync } from '@/lib/useAsync'
import { passwordError } from '@/pages/account/validation'

function PasswordForm() {
  const auth = useAuth()
  const toast = useToast()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [errors, setErrors] = useState<{
    current_password?: string
    new_password?: string
  }>({})
  const [saving, setSaving] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = {
      current_password: current ? undefined : 'Enter your current password.',
      new_password: passwordError(next),
    }
    setErrors(found)
    if (found.current_password || found.new_password) return
    setSaving(true)
    try {
      auth.applySession(await api.changePassword(current, next))
      setCurrent('')
      setNext('')
      toast.show({
        tone: 'success',
        title: 'Password changed',
        message: 'Other devices were signed out.',
      })
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fieldErrors).length) setErrors(err.fieldErrors)
      else
        toast.show({
          tone: 'error',
          title: 'Your password was not changed',
          message: 'Please try again.',
        })
    } finally {
      setSaving(false)
    }
  }

  return (
    <form noValidate onSubmit={submit} aria-label="Change password" className="flex flex-col gap-4">
      <FormField label="Current password" error={errors.current_password} required>
        {(field) => (
          <Input
            {...field}
            name="current_password"
            type="password"
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
          />
        )}
      </FormField>
      <FormField label="New password" hint="At least 12 characters." error={errors.new_password} required>
        {(field) => <Input {...field} name="new_password" type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />}
      </FormField>
      <AppButton type="submit" className="self-start" disabled={saving}>
        {saving ? 'Saving' : 'Change password'}
      </AppButton>
    </form>
  )
}

/** Set up an authenticator: scan, type the first code, keep the backup codes. */
function TwoStepSetup({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: (state: TwoStepState) => void }) {
  const toast = useToast()
  // Mounted only while open, so the secret is made when someone actually starts.
  const setup = useAsync(() => api.startTwoStep(), 'two-step-setup')
  const [code, setCode] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)
  const [codes, setCodes] = useState<string[] | null>(null)

  function close() {
    setCode('')
    setError(undefined)
    setCodes(null)
    onClose()
  }

  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!code.trim()) return setError('Enter the six-digit code from the app.')
    setBusy(true)
    try {
      const result = await api.confirmTwoStep(code)
      setCodes(result.backup_codes)
      onDone(result)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'That did not work. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} onClose={close} title={codes ? 'Keep your backup codes' : 'Set up two-step login'}>
      {codes ? (
        <div className="flex flex-col gap-4">
          <p className="text-fg-muted">Each code works once, if your phone is not to hand. They are shown only now: save them somewhere safe.</p>
          <ul aria-label="Backup codes" className="grid grid-cols-2 gap-2 rounded-app bg-surface p-4 font-mono text-fg">
            {codes.map((value) => (
              <li key={value}>{value}</li>
            ))}
          </ul>
          <div className="flex gap-2">
            <AppButton
              variant="secondary"
              onClick={() =>
                void navigator.clipboard?.writeText(codes.join('\n')).then(
                  () => toast.show({ tone: 'success', title: 'Codes copied' }),
                  () =>
                    toast.show({
                      tone: 'error',
                      title: 'Copy did not work',
                      message: 'Write them down instead.',
                    }),
                )
              }
            >
              <Copy aria-hidden="true" className="size-4" />
              Copy codes
            </AppButton>
            <AppButton onClick={close}>Done</AppButton>
          </div>
        </div>
      ) : setup.status === 'error' ? (
        <LoadError title={setup.error instanceof ApiError ? setup.error.message : 'Setup did not start'} onRetry={setup.retry} />
      ) : setup.status !== 'success' ? (
        <Skeleton lines={4} />
      ) : (
        <form noValidate onSubmit={confirm} className="flex flex-col gap-4">
          <ol className="flex list-decimal flex-col gap-1 pl-5 text-fg-muted">
            <li>Open an authenticator app on your phone.</li>
            <li>Scan this code, or type the key below.</li>
            <li>Enter the six-digit code the app shows.</li>
          </ol>
          <img
            src={setup.data.qr}
            alt="QR code to add this account to an authenticator app"
            className="size-44 self-center rounded-app border border-border bg-white p-2"
          />
          <p className="text-center font-mono text-sm tracking-[0.08em] text-fg">{setup.data.secret}</p>
          <FormField label="Six-digit code" error={error} required>
            {(field) => (
              <Input
                {...field}
                name="code"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={code}
                onChange={(e) => {
                  setCode(e.target.value)
                  setError(undefined)
                }}
              />
            )}
          </FormField>
          <AppButton type="submit" className="self-start" disabled={busy}>
            {busy ? 'Checking' : 'Turn on'}
          </AppButton>
        </form>
      )}
    </Modal>
  )
}

function TwoStep() {
  const toast = useToast()
  const state = useAsync(() => api.twoStep(), 'two-step')
  const [local, setLocal] = useState<TwoStepState | null>(null)
  const [dialog, setDialog] = useState<'setup' | 'off' | null>(null)
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)
  const current = local ?? (state.status === 'success' ? state.data : null)
  if (state.status === 'error' && !local) return <LoadError title="Your two-step login did not load" onRetry={state.retry} />
  if (!current) return <Skeleton lines={2} />

  async function turnOff() {
    if (!password) return setError('Enter your password to confirm.')
    setBusy(true)
    try {
      setLocal(await api.disableTwoStep(password))
      setDialog(null)
      setPassword('')
      toast.show({ tone: 'success', title: 'Two-step login is off' })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="flex items-center gap-4">
        <RowIcon icon={ShieldCheck} />
        <RowText
          label="Two-step login"
          sub={
            current.enabled
              ? `A code from your authenticator app at each sign-in · ${current.backup_codes_left} backup ${current.backup_codes_left === 1 ? 'code' : 'codes'} left`
              : 'Ask for a code from an authenticator app as well as your password'
          }
        />
        <StatusChip tone={current.enabled ? 'ok' : 'off'}>{current.enabled ? 'On' : 'Off'}</StatusChip>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {!current.enabled && <AppButton onClick={() => setDialog('setup')}>Set up</AppButton>}
        {current.enabled && !current.required && (
          <AppButton variant="secondary" onClick={() => setDialog('off')}>
            Turn off
          </AppButton>
        )}
        {current.required && <p className="text-meta text-fg-muted">Required for staff accounts, so it stays on.</p>}
      </div>
      {dialog === 'setup' && <TwoStepSetup open onClose={() => setDialog(null)} onDone={setLocal} />}
      <ConfirmDialog
        open={dialog === 'off'}
        title="Turn off two-step login?"
        confirmLabel="Turn off"
        busy={busy}
        onClose={() => {
          setDialog(null)
          setPassword('')
          setError(undefined)
        }}
        onConfirm={() => void turnOff()}
      >
        <p>Signing in will need only your password. Your backup codes stop working.</p>
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
    </>
  )
}

function Sessions() {
  const auth = useAuth()
  const navigate = useNavigate()
  const toast = useToast()
  const state = useAsync(() => api.sessions(), 'sessions')
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)

  async function everywhere() {
    setBusy(true)
    try {
      auth.applySession(await api.signOutEverywhere())
      navigate('/account/login', { replace: true })
    } catch (error) {
      toast.show({
        tone: 'error',
        title: 'That did not work',
        message: error instanceof Error ? error.message : undefined,
      })
      setBusy(false)
    }
  }

  return (
    <>
      {state.status === 'loading' && <Skeleton lines={2} />}
      {state.status === 'error' && <LoadError title="Your devices did not load" onRetry={state.retry} />}
      {state.status === 'success' && (
        <ul aria-label="Where you are signed in">
          {state.data.map((session) => (
            <li key={`${session.signed_in_at}-${session.device}`} className="flex min-h-14 items-center gap-4 border-b border-border py-2 last:border-b-0">
              <MonitorSmartphone aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} className="shrink-0 text-fg" />
              <span className="min-w-0 flex-1">
                <span className="block font-semibold text-fg">{session.device}</span>
                <span className="block text-meta text-fg-muted">
                  Signed in {formatDay(session.signed_in_at)}
                  {!session.current && !session.active_now && ` · last seen ${relativeDate(session.last_seen_at)}`}
                </span>
              </span>
              {session.current ? <StatusChip tone="ok">This device</StatusChip> : session.active_now && <StatusChip tone="off">Active now</StatusChip>}
            </li>
          ))}
        </ul>
      )}
      <AppButton variant="secondary" className="mt-4" onClick={() => setOpen(true)}>
        <LogOut aria-hidden="true" className="size-4" />
        Log out everywhere
      </AppButton>
      <ConfirmDialog
        open={open}
        title="Log out everywhere?"
        confirmLabel="Log out everywhere"
        busy={busy}
        onClose={() => setOpen(false)}
        onConfirm={() => void everywhere()}
      >
        <p>Every device signed in to this account will need your password again, including this one.</p>
      </ConfirmDialog>
    </>
  )
}

/** Settings · Security: the sign-in email, password, two-step login and where you are signed in. */
export function SecuritySection() {
  const auth = useAuth()
  if (!auth.user) return null
  return (
    <div className="flex flex-col gap-4">
      <Card title="Sign-in email">
        <div className="flex items-center gap-4">
          <RowIcon icon={Mail} />
          <span className="min-w-0 flex-1">
            <span className="block truncate font-semibold text-fg">{auth.user.email}</span>
            <span className="flex items-center gap-1.5 text-meta text-fg-muted">
              <EyeOff aria-hidden="true" className="size-3.5" />
              Only you can see this.
            </span>
          </span>
        </div>
      </Card>
      <Card title="Password">
        <PasswordForm />
      </Card>
      <Card title="Two-step login">
        <TwoStep />
      </Card>
      <Card title="Active sessions">
        <Sessions />
      </Card>
    </div>
  )
}

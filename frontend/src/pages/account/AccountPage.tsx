import { CalendarDays, EyeOff, LogOut, MailWarning, MonitorSmartphone, Trash2 } from 'lucide-react'
import { useState, type FormEvent, type ReactNode } from 'react'
import { Link, Navigate, useNavigate } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { ConfirmDialog } from '@/components/members/ConfirmDialog'
import { Badge, Button, Card, FormField, Input, Modal, Section, useToast } from '@/components/ui'
import { api, ApiError, type Appearance } from '@/lib/api'
import { chooseAppearance } from '@/lib/appearance'
import { cn } from '@/lib/cn'
import { formatEventDate } from '@/lib/format'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { FeedSection } from './FeedSection'
import { MembershipCard } from './MembershipCard'
import { displayNameError, passwordError } from './validation'

/** One account section: a site card with a Fraunces title. */
function Panel({ title, children, id }: { title: string; children: ReactNode; id: string }) {
  return (
    <Card as="article" aria-labelledby={id} className="scroll-mt-28 p-5 sm:p-8">
      <h2 id={id} className="text-[1.375rem] leading-[1.2] text-fg lg:text-[1.625rem]">
        {title}
      </h2>
      <div className="mt-5">{children}</div>
    </Card>
  )
}

function DisplayNameForm({ current }: { current: string }) {
  const auth = useAuth()
  const toast = useToast()
  const [value, setValue] = useState(current)
  const [error, setError] = useState<string>()
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = displayNameError(value)
    setError(found)
    if (found) return
    setSubmitting(true)
    try {
      auth.applySession(await api.changeDisplayName(value.trim()))
      toast.show({ tone: 'success', title: 'Display name updated' })
    } catch (err) {
      setError(err instanceof ApiError && err.fieldErrors.display_name ? err.fieldErrors.display_name : 'Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form noValidate onSubmit={submit} className="flex flex-col gap-4 sm:flex-row sm:items-start" aria-label="Change display name">
      <div className="flex-1">
        <FormField label="Display name" hint="The only name anyone else sees. Please avoid your real name." error={error} required>
          {(field) => <Input {...field} name="display_name" value={value} onChange={(e) => setValue(e.target.value)} />}
        </FormField>
      </div>
      <Button type="submit" variant="secondary" size="lg" className="sm:mt-[1.6875rem]" disabled={submitting || value.trim() === current} aria-busy={submitting}>
        {submitting ? 'Saving' : 'Save'}
      </Button>
    </form>
  )
}

/** Light or dark, for the website and the member app. Saved on the account and in this browser. */
function AppearanceChoice({ current }: { current: Appearance }) {
  const auth = useAuth()
  const toast = useToast()

  async function choose(next: Appearance) {
    try {
      const session = await chooseAppearance(next, true)
      if (session) auth.applySession(session)
    } catch {
      toast.show({ tone: 'error', title: 'Your choice was not saved', message: 'It applies in this browser for now.' })
    }
  }

  return (
    <div>
      <div role="radiogroup" aria-label="Appearance" className="inline-flex rounded-full border border-border p-[3px] text-sm font-semibold">
        {(['light', 'dark'] as const).map((value) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={current === value}
            onClick={() => void choose(value)}
            className={cn(
              'inline-flex h-[34px] items-center rounded-full px-[18px] transition-colors duration-150',
              current === value ? 'bg-fg text-canvas' : 'text-fg-muted hover:text-fg',
            )}
          >
            {value === 'light' ? 'Light' : 'Dark'}
          </button>
        ))}
      </div>
      <p className="mt-3 text-sm text-fg-muted">Light is the default. Your choice follows you to every device you sign in on.</p>
    </div>
  )
}

function PasswordForm() {
  const auth = useAuth()
  const toast = useToast()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [errors, setErrors] = useState<{ current_password?: string; new_password?: string }>({})
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = { current_password: current ? undefined : 'Enter your current password.', new_password: passwordError(next) }
    setErrors(found)
    if (found.current_password || found.new_password) return
    setSubmitting(true)
    try {
      auth.applySession(await api.changePassword(current, next))
      setCurrent('')
      setNext('')
      toast.show({ tone: 'success', title: 'Password changed' })
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fieldErrors).length) setErrors(err.fieldErrors)
      else toast.show({ tone: 'error', title: 'Your password was not changed', message: 'Please try again.' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form noValidate onSubmit={submit} className="flex flex-col gap-5" aria-label="Change password">
      <FormField label="Current password" error={errors.current_password} required>
        {(field) => (
          <Input {...field} name="current_password" type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
        )}
      </FormField>
      <FormField label="New password" hint="At least 12 characters." error={errors.new_password} required>
        {(field) => (
          <Input {...field} name="new_password" type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
        )}
      </FormField>
      <Button type="submit" variant="secondary" size="lg" className="self-start" disabled={submitting} aria-busy={submitting}>
        {submitting ? 'Saving' : 'Change password'}
      </Button>
    </form>
  )
}

function UpcomingRSVPs() {
  const state = useAsync(() => api.myRSVPs(), 'my-rsvps')
  if (state.status === 'loading') return <LoadingState label="Loading your RSVPs" />
  if (state.status === 'error') return <ErrorState title="Your RSVPs did not load" onRetry={state.retry} />
  if (state.data.length === 0) {
    return (
      <p className="text-fg-muted">
        No plans yet. Find an evening on the{' '}
        <Link to="/events" className="font-semibold text-link hover:text-primary-hover">
          events page
        </Link>
        .
      </p>
    )
  }
  return (
    <ul className="divide-y divide-border">
      {state.data.map((item) => (
        <li key={item.event.slug} className="flex flex-wrap items-center justify-between gap-3 py-4 first:pt-0 last:pb-0">
          <div>
            <Link to={`/events/${item.event.slug}`} className="font-display text-xl text-fg hover:text-link">
              {item.event.title}
            </Link>
            <p className="mt-1 flex items-center gap-2 text-sm text-fg-muted">
              <CalendarDays aria-hidden="true" className="size-4 text-link" />
              <time dateTime={item.event.starts_at}>{formatEventDate(item.event.starts_at)}</time>
            </p>
          </div>
          <div className="flex items-center gap-2">
            {item.party_size > 1 && <Badge tone="full">Party of {item.party_size}</Badge>}
            <Badge tone={item.status === 'going' ? 'going' : 'wait'}>{item.status === 'going' ? 'Going' : 'On the waitlist'}</Badge>
          </div>
        </li>
      ))}
    </ul>
  )
}

function SignOutEverywhere() {
  const auth = useAuth()
  const navigate = useNavigate()
  const toast = useToast()
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)

  async function confirm() {
    setBusy(true)
    try {
      auth.applySession(await api.signOutEverywhere())
      navigate('/account/login', { replace: true })
    } catch (error) {
      toast.show({ tone: 'error', title: 'That did not work', message: error instanceof Error ? error.message : undefined })
      setBusy(false)
    }
  }

  return (
    <>
      <p className="text-fg-muted">
        Lost a phone, or signed in on a shared computer? This signs you out on every device, including this one.
      </p>
      <Button variant="secondary" size="lg" className="mt-5" onClick={() => setOpen(true)}>
        <MonitorSmartphone aria-hidden="true" className="size-4" />
        Sign out everywhere
      </Button>
      <ConfirmDialog
        open={open}
        title="Sign out everywhere?"
        confirmLabel="Sign out everywhere"
        busy={busy}
        onClose={() => setOpen(false)}
        onConfirm={() => void confirm()}
      >
        <p>Every device signed in to this account will need your password again, including this one.</p>
      </ConfirmDialog>
    </>
  )
}

function DeleteAccount() {
  const auth = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string>()
  const [submitting, setSubmitting] = useState(false)

  async function confirm() {
    if (!password) {
      setError('Enter your password to confirm.')
      return
    }
    setSubmitting(true)
    try {
      auth.applySession(await api.deleteAccount(password))
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError && err.fieldErrors.password ? err.fieldErrors.password : 'Please try again.')
      setSubmitting(false)
    }
  }

  return (
    <>
      <p className="text-fg-muted">
        Deleting your account removes your profile and every RSVP straight away. Any message you sent us is kept
        without your name, email or phone number. An open membership is cancelled, and payment records are kept for
        our accounts with nothing that identifies you. This cannot be undone.
      </p>
      <Button variant="secondary" size="lg" className="mt-5 border-danger text-danger hover:border-danger" onClick={() => setOpen(true)}>
        <Trash2 aria-hidden="true" className="size-4" />
        Delete my account
      </Button>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Delete your account?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Keep my account
            </Button>
            <Button onClick={confirm} disabled={submitting} aria-busy={submitting}>
              {submitting ? 'Deleting' : 'Delete for good'}
            </Button>
          </>
        }
      >
        <p className="mb-5 text-fg-muted">Your RSVPs will be released to the waitlist. Enter your password to confirm.</p>
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
      </Modal>
    </>
  )
}

function VerifyBanner() {
  const toast = useToast()
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)

  async function resend() {
    setSending(true)
    try {
      await api.resendVerification()
      setSent(true)
    } catch {
      toast.show({ tone: 'error', title: 'We could not send a new link', message: 'Please try again later.' })
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex flex-col gap-4 rounded-card bg-blush p-5 sm:flex-row sm:items-center">
      <MailWarning aria-hidden="true" className="size-6 shrink-0 text-link" />
      <p className="flex-1 text-sm text-fg-muted-tint">Confirm your email to RSVP. Check your inbox for our link.</p>
      {sent ? (
        <p role="status" className="text-sm text-link">
          A new link is on its way.
        </p>
      ) : (
        <Button variant="secondary" onClick={resend} disabled={sending} aria-busy={sending}>
          {sending ? 'Sending' : 'Send a new link'}
        </Button>
      )}
    </div>
  )
}

export function AccountPage() {
  useDocumentMeta({ title: 'My account', noindex: true })
  const auth = useAuth()
  const navigate = useNavigate()
  const [leaving, setLeaving] = useState(false)

  if (auth.status === 'loading') {
    return (
      <Section width="narrow">
        <LoadingState label="Loading your account" />
      </Section>
    )
  }
  // After "Log out" the page goes home, not to the login form.
  if (!auth.user) return <Navigate to={leaving ? '/' : '/account/login?next=%2Faccount'} replace />
  const user = auth.user

  return (
    <Section width="narrow" spacing="none" className="pb-16 pt-7 lg:pb-24 lg:pt-16">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-3">
          <p className="text-xs font-semibold uppercase tracking-[0.06em] text-link">My account</p>
          <h1 className="text-[2.25rem] font-light leading-[1.05] text-fg lg:text-h1">{user.display_name}</h1>
        </div>
        <Button
          variant="secondary"
          onClick={async () => {
            setLeaving(true)
            await auth.logout()
            navigate('/', { replace: true })
          }}
        >
          <LogOut aria-hidden="true" className="size-4" />
          Log out
        </Button>
      </header>

      <div className="mt-8 flex flex-col gap-4 lg:mt-10 lg:gap-6">
        {!user.email_verified && <VerifyBanner />}
        <MembershipCard />
        <Panel id="rsvps" title="Upcoming plans">
          <UpcomingRSVPs />
        </Panel>
        <FeedSection />
        <Panel id="profile" title="Profile">
          <DisplayNameForm key={user.display_name} current={user.display_name} />
          <div className="mt-6 border-t border-border pt-5">
            <p className="text-sm font-semibold text-fg">Email</p>
            <p className="mt-1 text-fg-muted">{user.email}</p>
            <p className="mt-2 flex items-center gap-2 text-xs text-fg-muted">
              <EyeOff aria-hidden="true" className="size-3.5" />
              Only you can see this.
            </p>
          </div>
        </Panel>
        <Panel id="appearance" title="Appearance">
          <AppearanceChoice current={user.appearance} />
        </Panel>
        <Panel id="password" title="Password">
          <PasswordForm />
        </Panel>
        <Panel id="sessions" title="Devices">
          <SignOutEverywhere />
        </Panel>
        <Panel id="delete" title="Delete account">
          <DeleteAccount />
        </Panel>
      </div>
    </Section>
  )
}

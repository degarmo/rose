import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { Button, FormField, Input } from '@/components/ui'
import { api, ApiError, type Session } from '@/lib/api'
import { safeNextPath } from '@/lib/format'
import { landingAfterLogin } from '@/lib/memberApp'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { AccountShell, FORM_ALERT } from './AccountShell'
import { emailError } from './validation'

export function LoginPage() {
  useDocumentMeta({ title: 'Log in', noindex: true })
  const auth = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = safeNextPath(params.get('next'))
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [twoStep, setTwoStep] = useState(false)
  const [code, setCode] = useState('')

  function signedIn(session: Session) {
    auth.applySession(session)
    const landing = landingAfterLogin(session.user, params.get('next'), next)
    // The admin dashboard is outside this app: a full page load.
    if (/^https?:\/\//.test(landing)) window.location.assign(landing)
    else navigate(landing, { replace: true })
  }

  async function submitCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError('')
    if (!code.trim()) return setFormError('Enter the code from your authenticator app, or a backup code.')
    setSubmitting(true)
    try {
      signedIn(await api.loginTwoStep(code))
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : 'Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = { email: emailError(email), password: password ? undefined : 'Enter your password.' }
    setErrors(found)
    setFormError('')
    if (found.email || found.password) return
    setSubmitting(true)
    try {
      const session = await api.login(email.trim(), password)
      if (session.two_step) {
        auth.applySession(session)
        setTwoStep(true)
      } else signedIn(session)
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : 'Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const query = params.get('next') ? `?next=${encodeURIComponent(next)}` : ''

  if (twoStep) {
    return (
      <AccountShell title="Enter your code" lede="Your account has two-step login. Open your authenticator app for the six-digit code.">
        <form noValidate onSubmit={submitCode} className="flex flex-col gap-5" aria-label="Two-step login">
          {formError && (
            <p role="alert" className={FORM_ALERT}>
              {formError}
            </p>
          )}
          <FormField label="Code" hint="No phone to hand? Use one of your backup codes." required>
            {(field) => (
              <Input {...field} name="code" inputMode="numeric" autoComplete="one-time-code" autoFocus value={code} onChange={(e) => setCode(e.target.value)} />
            )}
          </FormField>
          <Button type="submit" size="lg" disabled={submitting} aria-busy={submitting} className="self-start">
            {submitting ? 'Checking' : 'Continue'}
          </Button>
          <button
            type="button"
            onClick={() => {
              setTwoStep(false)
              setCode('')
              setPassword('')
              setFormError('')
            }}
            className="self-start text-sm text-fg-muted underline-offset-4 hover:text-fg hover:underline"
          >
            Start again
          </button>
        </form>
      </AccountShell>
    )
  }

  return (
    <AccountShell
      title="Welcome back"
      footer={
        <>
          New here?{' '}
          <Link to={`/account/register${query}`} className="font-semibold text-link hover:text-primary-hover">
            Create an account
          </Link>
        </>
      }
    >
      <form noValidate onSubmit={submit} className="flex flex-col gap-5" aria-label="Log in">
        {formError && (
          <p role="alert" className={FORM_ALERT}>
            {formError}
          </p>
        )}
        <FormField label="Email" error={errors.email} required>
          {(field) => (
            <Input {...field} name="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          )}
        </FormField>
        <FormField label="Password" error={errors.password} required>
          {(field) => (
            <Input
              {...field}
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          )}
        </FormField>
        <Button type="submit" size="lg" disabled={submitting} aria-busy={submitting} className="self-start">
          {submitting ? 'Signing in' : 'Log in'}
        </Button>
        <Link to="/account/forgot" className="self-start text-sm text-fg-muted underline-offset-4 hover:text-fg hover:underline">
          Forgot your password?
        </Link>
      </form>
    </AccountShell>
  )
}

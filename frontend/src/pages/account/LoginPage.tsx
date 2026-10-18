import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { Button, FormField, Input } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import { safeNextPath } from '@/lib/format'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { AccountShell } from './AccountShell'
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

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = { email: emailError(email), password: password ? undefined : 'Enter your password.' }
    setErrors(found)
    setFormError('')
    if (found.email || found.password) return
    setSubmitting(true)
    try {
      auth.applySession(await api.login(email.trim(), password))
      navigate(next, { replace: true })
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : 'Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const query = params.get('next') ? `?next=${encodeURIComponent(next)}` : ''

  return (
    <AccountShell
      title="Welcome back"
      footer={
        <>
          New here?{' '}
          <Link to={`/account/register${query}`} className="text-accent underline underline-offset-4">
            Create an account
          </Link>
        </>
      }
    >
      <form noValidate onSubmit={submit} className="flex flex-col gap-5" aria-label="Log in">
        {formError && (
          <p role="alert" className="rounded-xl border border-danger/50 p-3 text-sm text-danger">
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
        <Button type="submit" size="lg" disabled={submitting} aria-busy={submitting}>
          {submitting ? 'Signing in' : 'Log in'}
        </Button>
        <Link to="/account/forgot" className="text-center text-sm text-fg-muted underline-offset-4 hover:text-fg hover:underline">
          Forgot your password?
        </Link>
      </form>
    </AccountShell>
  )
}

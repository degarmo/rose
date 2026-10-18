import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { Button, FormField, Input } from '@/components/ui'
import { api } from '@/lib/api'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { AccountShell } from './AccountShell'
import { emailError } from './validation'

export function ForgotPasswordPage() {
  useDocumentMeta({ title: 'Reset your password', noindex: true })
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string>()
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [sent, setSent] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = emailError(email)
    setError(found)
    if (found) return
    setSubmitting(true)
    setFormError('')
    try {
      await api.requestPasswordReset(email.trim())
      setSent(true)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AccountShell
      title="Reset your password"
      lede={sent ? undefined : 'Enter the email you signed up with and we will send a reset link.'}
      footer={
        <Link to="/account/login" className="text-accent underline underline-offset-4">
          Back to log in
        </Link>
      }
    >
      {sent ? (
        <p role="status" className="leading-relaxed text-fg-muted">
          If that email has an account, a reset link is on its way. It works for two hours.
        </p>
      ) : (
        <form noValidate onSubmit={submit} className="flex flex-col gap-5" aria-label="Reset your password">
          {formError && (
            <p role="alert" className="rounded-xl border border-danger/50 p-3 text-sm text-danger">
              {formError}
            </p>
          )}
          <FormField label="Email" error={error} required>
            {(field) => (
              <Input {...field} name="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            )}
          </FormField>
          <Button type="submit" size="lg" disabled={submitting} aria-busy={submitting}>
            {submitting ? 'Sending' : 'Send reset link'}
          </Button>
        </form>
      )}
    </AccountShell>
  )
}

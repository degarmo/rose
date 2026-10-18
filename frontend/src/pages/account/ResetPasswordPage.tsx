import { CircleCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Button, ButtonLink, FormField, Input } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import { fragmentParams } from '@/lib/format'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { AccountShell } from './AccountShell'
import { passwordError } from './validation'

export function ResetPasswordPage() {
  useDocumentMeta({ title: 'Choose a new password', noindex: true })
  const [{ uid, token }] = useState(() => {
    const params = fragmentParams(window.location.hash)
    return { uid: params.get('uid') ?? '', token: params.get('token') ?? '' }
  })
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState<{ password?: string; confirm?: string }>({})
  const [formError, setFormError] = useState(uid && token ? '' : 'This link is incomplete. Request a new one.')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = {
      password: passwordError(password),
      confirm: confirm === password ? undefined : 'The two passwords do not match.',
    }
    setErrors(found)
    if (found.password || found.confirm) return
    setSubmitting(true)
    setFormError('')
    try {
      await api.confirmPasswordReset(uid, token, password)
      window.history.replaceState(null, '', window.location.pathname)
      setDone(true)
    } catch (error) {
      if (error instanceof ApiError && error.fieldErrors.new_password) {
        setErrors({ password: error.fieldErrors.new_password })
      } else {
        setFormError(error instanceof Error ? error.message : 'Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AccountShell title="Choose a new password">
      {done ? (
        <div role="status">
          <CircleCheck aria-hidden="true" className="size-8 text-success" />
          <p className="mt-4 text-fg-muted">Your password has been changed.</p>
          <ButtonLink to="/account/login" size="lg" className="mt-8 w-full">
            Log in
          </ButtonLink>
        </div>
      ) : (
        <form noValidate onSubmit={submit} className="flex flex-col gap-5" aria-label="Choose a new password">
          {formError && (
            <p role="alert" className="rounded-xl border border-danger/50 p-3 text-sm text-danger">
              {formError}
            </p>
          )}
          <FormField label="New password" hint="At least 12 characters." error={errors.password} required>
            {(field) => (
              <Input {...field} name="password" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            )}
          </FormField>
          <FormField label="Type it again" error={errors.confirm} required>
            {(field) => (
              <Input {...field} name="confirm" type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
            )}
          </FormField>
          <Button type="submit" size="lg" disabled={submitting || !uid || !token} aria-busy={submitting}>
            {submitting ? 'Saving' : 'Save new password'}
          </Button>
        </form>
      )}
    </AccountShell>
  )
}

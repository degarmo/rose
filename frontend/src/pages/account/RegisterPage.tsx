import { MailCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router'
import { Button, FormField, Input } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import { safeNextPath } from '@/lib/format'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { AccountShell } from './AccountShell'
import { displayNameError, emailError, firstError, passwordError } from './validation'

type Field = 'email' | 'display_name' | 'password'

export function RegisterPage() {
  useDocumentMeta({ title: 'Create an account', noindex: true })
  const [params] = useSearchParams()
  const next = safeNextPath(params.get('next'), '')
  const [values, setValues] = useState({ email: '', display_name: '', password: '' })
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  function validate(field: Field, value: string) {
    if (field === 'email') return emailError(value)
    if (field === 'display_name') return displayNameError(value)
    return passwordError(value)
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = {
      email: validate('email', values.email),
      display_name: validate('display_name', values.display_name),
      password: validate('password', values.password),
    }
    setErrors(found)
    setFormError('')
    if (firstError(found)) return
    setSubmitting(true)
    try {
      await api.register({ ...values, email: values.email.trim(), display_name: values.display_name.trim() })
      setDone(true)
    } catch (error) {
      if (error instanceof ApiError && Object.keys(error.fieldErrors).length) {
        setErrors(error.fieldErrors)
      } else {
        setFormError(error instanceof Error ? error.message : 'Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (done) {
    return (
      <AccountShell title="Check your email">
        <div role="status">
          <MailCheck aria-hidden="true" className="size-8 text-highlight" />
          <p className="mt-4 leading-relaxed text-fg-muted">
            We sent a link to <span className="text-fg">{values.email.trim()}</span>. Open it within three days to
            confirm your address, then log in.
          </p>
          <Link
            to={`/account/login${next ? `?next=${encodeURIComponent(next)}` : ''}`}
            className="mt-8 inline-block text-accent underline underline-offset-4"
          >
            Go to log in
          </Link>
        </div>
      </AccountShell>
    )
  }

  const field = (name: Field) => ({
    value: values[name],
    onChange: (e: { target: { value: string } }) => {
      setValues((current) => ({ ...current, [name]: e.target.value }))
      if (errors[name]) setErrors((current) => ({ ...current, [name]: validate(name, e.target.value) }))
    },
    onBlur: () => setErrors((current) => ({ ...current, [name]: validate(name, values[name]) })),
  })

  return (
    <AccountShell
      title="Create an account"
      lede="A free account lets you RSVP. Only our hosts see who is coming."
      footer={
        <>
          Already have one?{' '}
          <Link to="/account/login" className="text-accent underline underline-offset-4">
            Log in
          </Link>
        </>
      }
    >
      <form noValidate onSubmit={submit} className="flex flex-col gap-5" aria-label="Create an account">
        {formError && (
          <p role="alert" className="rounded-xl border border-danger/50 p-3 text-sm text-danger">
            {formError}
          </p>
        )}
        <FormField label="Email" hint="Private. Never shown to anyone." error={errors.email} required>
          {(props) => <Input {...props} name="email" type="email" autoComplete="email" {...field('email')} />}
        </FormField>
        <FormField
          label="Display name"
          hint="Please don't use your real name. This is the only name anyone else sees."
          error={errors.display_name}
          required
        >
          {(props) => <Input {...props} name="display_name" autoComplete="off" spellCheck={false} {...field('display_name')} />}
        </FormField>
        <FormField label="Password" hint="At least 12 characters." error={errors.password} required>
          {(props) => <Input {...props} name="password" type="password" autoComplete="new-password" {...field('password')} />}
        </FormField>
        <Button type="submit" size="lg" disabled={submitting} aria-busy={submitting}>
          {submitting ? 'Creating account' : 'Create account'}
        </Button>
      </form>
    </AccountShell>
  )
}

import { useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { Copy, CopyHeading } from '@/components/content/Copy'
import { PageHero } from '@/components/content/PageHero'
import { ErrorState, LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { Button, Card, CheckboxBox, FormField, Input, Section, Textarea, useToast } from '@/components/ui'
import { api, ApiError, type Choice, type FieldErrors, type VolunteerPayload } from '@/lib/api'
import { cn } from '@/lib/cn'
import { usePageContent } from '@/lib/pageContent'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { SentPanel } from './SentPanel'
import { validateVolunteer, VOLUNTEER_FIELDS as FIELDS } from './volunteerValidation'

const EMPTY: VolunteerPayload = {
  contact_name: '',
  contact_email: '',
  interests: [],
  availability: [],
  experience_note: '',
  website: '',
}

function CheckboxGroup({
  legend,
  name,
  choices,
  selected,
  error,
  onChange,
}: {
  legend: string
  name: string
  choices: Choice[]
  selected: string[]
  error?: string
  onChange: (next: string[]) => void
}) {
  const errorId = `${name}-error`
  return (
    <fieldset aria-describedby={error ? errorId : undefined} className="flex flex-col gap-1.5">
      <legend className="mb-1.5 text-sm font-semibold text-fg">{legend}</legend>
      <div className="grid gap-2 sm:grid-cols-2">
        {choices.map((choice) => (
          <label
            key={choice.value}
            className={cn(
              'flex min-h-12 cursor-pointer items-center gap-3 rounded-field border px-4 py-2 text-sm text-fg transition-colors',
              selected.includes(choice.value) ? 'border-primary bg-tier-selected' : error ? 'border-danger' : 'border-border hover:border-fg-muted',
            )}
          >
            <CheckboxBox
              name={name}
              value={choice.value}
              checked={selected.includes(choice.value)}
              onChange={(event) =>
                onChange(event.target.checked ? [...selected, choice.value] : selected.filter((value) => value !== choice.value))
              }
            />
            {choice.label}
          </label>
        ))}
      </div>
      {error && (
        <p id={errorId} className="text-[0.8125rem] text-danger">
          {error}
        </p>
      )}
    </fieldset>
  )
}

function VolunteerForm() {
  const auth = useAuth()
  const toast = useToast()
  const options = useAsync(() => api.volunteerOptions(), 'volunteer-options')
  // Signed in: start from their display name and email; the signup is linked to the account.
  const [values, setValues] = useState<VolunteerPayload>(() => ({
    ...EMPTY,
    contact_name: auth.user?.display_name ?? '',
    contact_email: auth.user?.email ?? '',
  }))
  const [errors, setErrors] = useState<FieldErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [sent, setSent] = useState(false)
  const formRef = useRef<HTMLFormElement>(null)
  const successRef = useRef<HTMLHeadingElement>(null)

  if (options.status === 'loading') return <LoadingState label="Loading the form" />
  if (options.status === 'error') return <ErrorState title="The form did not load" onRetry={options.retry} />

  function set<K extends keyof VolunteerPayload>(field: K, value: VolunteerPayload[K]) {
    setValues((current) => ({ ...current, [field]: value }))
    if (errors[field]) setErrors((current) => ({ ...current, [field]: undefined }))
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const clientErrors = validateVolunteer(values)
    setErrors(clientErrors)
    const first = FIELDS.find((field) => clientErrors[field])
    if (first) {
      formRef.current?.querySelector<HTMLElement>(`[name="${first}"]`)?.focus()
      return
    }
    setSubmitting(true)
    try {
      await api.sendVolunteerSignup(values)
      setSent(true)
      requestAnimationFrame(() => successRef.current?.focus())
    } catch (error) {
      if (error instanceof ApiError && Object.keys(error.fieldErrors).length > 0) {
        setErrors(error.fieldErrors)
        toast.show({ tone: 'error', title: 'Please check the highlighted fields.' })
      } else {
        toast.show({
          tone: 'error',
          title: 'Your note was not sent',
          message: error instanceof Error ? error.message : 'Please try again in a moment.',
        })
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (sent) {
    return (
      <SentPanel headingRef={successRef} title="Thank you for offering to help.">
        A volunteer coordinator will reply to {values.contact_email.trim()} to talk about what might suit you.
      </SentPanel>
    )
  }

  return (
    <form ref={formRef} noValidate onSubmit={submit} className="flex flex-col gap-5" aria-label="Volunteer form">
      <div className="grid gap-5 sm:grid-cols-2 sm:gap-4">
        <FormField label="Name or display name" error={errors.contact_name} required>
          {(field) => (
            <Input
              {...field}
              name="contact_name"
              autoComplete="nickname"
              value={values.contact_name}
              onChange={(event) => set('contact_name', event.target.value)}
            />
          )}
        </FormField>
        <FormField label="Email" error={errors.contact_email} required>
          {(field) => (
            <Input
              {...field}
              name="contact_email"
              type="email"
              autoComplete="email"
              inputMode="email"
              value={values.contact_email}
              onChange={(event) => set('contact_email', event.target.value)}
            />
          )}
        </FormField>
      </div>
      <CheckboxGroup
        legend="How would you like to help?"
        name="interests"
        choices={options.data.interests}
        selected={values.interests}
        error={errors.interests}
        onChange={(next) => set('interests', next)}
      />
      <CheckboxGroup
        legend="When are you usually free?"
        name="availability"
        choices={options.data.availability}
        selected={values.availability}
        error={errors.availability}
        onChange={(next) => set('availability', next)}
      />
      <FormField
        label="Anything about your experience"
        hint="Teaching, hosting, trades, admin: whatever you would like us to know."
        error={errors.experience_note}
      >
        {(field) => (
          <Textarea
            {...field}
            name="experience_note"
            rows={5}
            maxLength={2000}
            value={values.experience_note}
            onChange={(event) => set('experience_note', event.target.value)}
          />
        )}
      </FormField>

      {/* Honeypot: hidden from people and assistive tech, tempting to bots. */}
      <div aria-hidden="true" className="absolute -left-[9999px] h-px w-px overflow-hidden">
        <label>
          Website
          <input
            type="text"
            name="website"
            tabIndex={-1}
            autoComplete="off"
            value={values.website}
            onChange={(event) => set('website', event.target.value)}
          />
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <Button type="submit" size="lg" disabled={submitting} aria-busy={submitting}>
          {submitting ? 'Sending' : 'Send'}
        </Button>
        <p className="text-[0.8125rem] text-fg-muted">
          Only our volunteer coordinators see this.{' '}
          <Link to="/privacy" className="underline underline-offset-4 hover:text-fg">
            Privacy
          </Link>
        </p>
      </div>
    </form>
  )
}

/** Volunteer (no design: roles as site cards, the form laid out like Contact). */
export function VolunteerPage() {
  useDocumentMeta({
    title: 'Volunteer',
    description: 'Why volunteer, the roles you can take on, and how to offer your time.',
  })
  const copy = usePageContent('volunteer')
  const auth = useAuth()
  const roles = copy.status === 'loading' ? [1, 2, 3] : copy.items('roles')

  return (
    <>
      <PageHero copy={copy} image="volunteer-hero.webp" placeholder="rose" />

      <Section width="narrow" aria-labelledby="why">
        <CopyHeading copy={copy} prefix="why" id="why" />
      </Section>

      <Section tone="surface" aria-labelledby="roles">
        <CopyHeading copy={copy} prefix="roles" id="roles" />
        <ul className="mt-8 grid gap-4 sm:grid-cols-2 lg:mt-10 lg:grid-cols-3 lg:gap-6">
          {roles.map((n) => (
            <li key={n}>
              <Card className="h-full p-5 lg:p-6">
                <Copy copy={copy} k={`roles.${n}.title`} as="h3" className="text-xl text-fg lg:text-card-title" />
                <Copy copy={copy} k={`roles.${n}.body`} lines={3} className="mt-2 text-sm text-fg-muted" />
              </Card>
            </li>
          ))}
        </ul>
      </Section>

      <Section aria-labelledby="offer">
        <div className="grid gap-8 lg:grid-cols-2 lg:gap-24">
          <CopyHeading copy={copy} prefix="form" id="offer" />
          <div className="w-full lg:max-w-[520px]">
            {auth.status === 'loading' ? (
              <LoadingState label="Loading the form" />
            ) : (
              <VolunteerForm key={auth.user?.display_name ?? 'signed-out'} />
            )}
          </div>
        </div>
      </Section>
    </>
  )
}

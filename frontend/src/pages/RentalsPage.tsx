import { Check } from 'lucide-react'
import { useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { Copy, CopyHeading } from '@/components/content/Copy'
import { PageHero } from '@/components/content/PageHero'
import { LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { Button, Card, Checkbox, FormField, Input, Section, Select, Textarea, useToast } from '@/components/ui'
import { api, ApiError, type FieldErrors, type RentalInquiryPayload } from '@/lib/api'
import { usePageContent, type PageCopy } from '@/lib/pageContent'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import {
  DURATIONS,
  EMPTY_RENTAL,
  PHOTOSHOOT_PROMISE,
  RENTAL_FIELDS,
  RENTAL_TYPES,
  validateRental,
  validateRentalField,
  type RentalField,
} from './rentalsValidation'
import { SENT_ACTION, SentPanel } from './SentPanel'

function CopyList({ copy, prefix }: { copy: PageCopy; prefix: string }) {
  const items = copy.status === 'loading' ? [1, 2, 3] : copy.items(prefix)
  return (
    <ul className="mt-4 flex flex-col gap-2.5">
      {items.map((n) => (
        <li key={n} className="flex gap-3 text-fg-muted">
          <Check aria-hidden="true" className="mt-[5px] size-4 shrink-0 text-link" />
          <Copy copy={copy} k={`${prefix}.${n}`} as="span" />
        </li>
      ))}
    </ul>
  )
}

export function RentalInquiryForm() {
  const auth = useAuth()
  const toast = useToast()
  // Signed-in people start with their display name and email filled in.
  const [values, setValues] = useState<RentalInquiryPayload>(() => ({
    ...EMPTY_RENTAL,
    contact_name: auth.user?.display_name ?? '',
    contact_email: auth.user?.email ?? '',
  }))
  const [errors, setErrors] = useState<FieldErrors>({})
  const [touched, setTouched] = useState<Partial<Record<RentalField, boolean>>>({})
  const [submitting, setSubmitting] = useState(false)
  const [sent, setSent] = useState(false)
  const formRef = useRef<HTMLFormElement>(null)
  const successRef = useRef<HTMLHeadingElement>(null)

  function change<K extends keyof RentalInquiryPayload>(field: K, value: RentalInquiryPayload[K]) {
    const next = { ...values, [field]: value }
    setValues(next)
    if (field !== 'website' && touched[field as RentalField]) {
      setErrors((current) => ({ ...current, [field]: validateRentalField(field as RentalField, next) }))
    }
  }

  function blur(field: RentalField) {
    setTouched((current) => ({ ...current, [field]: true }))
    setErrors((current) => ({ ...current, [field]: validateRentalField(field, values) }))
  }

  function focusFirstError(fieldErrors: FieldErrors) {
    const first = RENTAL_FIELDS.find((field) => fieldErrors[field])
    if (first) formRef.current?.querySelector<HTMLElement>(`[name="${first}"]`)?.focus()
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const clientErrors = validateRental(values)
    setTouched(Object.fromEntries(RENTAL_FIELDS.map((field) => [field, true])))
    setErrors(clientErrors)
    if (Object.keys(clientErrors).length > 0) {
      focusFirstError(clientErrors)
      return
    }
    setSubmitting(true)
    try {
      await api.sendRentalInquiry({ ...values, alternate_date: values.alternate_date || null })
      setSent(true)
      setValues(EMPTY_RENTAL)
      setTouched({})
      requestAnimationFrame(() => successRef.current?.focus())
    } catch (error) {
      if (error instanceof ApiError && Object.keys(error.fieldErrors).length > 0) {
        setErrors(error.fieldErrors)
        focusFirstError(error.fieldErrors)
        toast.show({ tone: 'error', title: 'Please check the highlighted fields.' })
      } else if (error instanceof ApiError && error.isRateLimited) {
        toast.show({ tone: 'error', title: 'Too many requests', message: 'Please wait a while before sending another.' })
      } else {
        toast.show({
          tone: 'error',
          title: 'Your request was not sent',
          message: error instanceof Error ? error.message : 'Please try again in a moment.',
        })
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (sent) {
    return (
      <SentPanel
        headingRef={successRef}
        title="Thank you. Your request is with us."
        actions={
          <button type="button" onClick={() => setSent(false)} className={SENT_ACTION}>
            Send another request
          </button>
        }
      >
        A volunteer will reply by email, usually within a few days. Nothing is booked until we confirm with you.
      </SentPanel>
    )
  }

  return (
    <form ref={formRef} noValidate onSubmit={submit} className="flex flex-col gap-5" aria-label="Rental inquiry">
      <div className="grid gap-5 sm:grid-cols-2 sm:gap-4">
        <FormField label="Name or display name" error={errors.contact_name} required>
          {(field) => (
            <Input
              {...field}
              name="contact_name"
              autoComplete="nickname"
              value={values.contact_name}
              onChange={(event) => change('contact_name', event.target.value)}
              onBlur={() => blur('contact_name')}
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
              onChange={(event) => change('contact_email', event.target.value)}
              onBlur={() => blur('contact_email')}
            />
          )}
        </FormField>
      </div>
      <div className="grid gap-5 sm:grid-cols-2 sm:gap-4">
        <FormField label="Phone" hint="Only if you would like a call back." error={errors.contact_phone}>
          {(field) => (
            <Input
              {...field}
              name="contact_phone"
              type="tel"
              autoComplete="tel"
              value={values.contact_phone}
              onChange={(event) => change('contact_phone', event.target.value)}
              onBlur={() => blur('contact_phone')}
            />
          )}
        </FormField>
        <FormField label="What is it for?" error={errors.type} required>
          {(field) => (
            <Select
              {...field}
              name="type"
              options={[{ value: '', label: 'Choose one' }, ...RENTAL_TYPES]}
              value={values.type}
              onChange={(event) => change('type', event.target.value as RentalInquiryPayload['type'])}
              onBlur={() => blur('type')}
            />
          )}
        </FormField>
      </div>
      <div className="grid gap-5 sm:grid-cols-2 sm:gap-4">
        <FormField label="Preferred date" error={errors.preferred_date} required>
          {(field) => (
            <Input
              {...field}
              name="preferred_date"
              type="date"
              value={values.preferred_date}
              onChange={(event) => change('preferred_date', event.target.value)}
              onBlur={() => blur('preferred_date')}
            />
          )}
        </FormField>
        <FormField label="Second choice" error={errors.alternate_date}>
          {(field) => (
            <Input
              {...field}
              name="alternate_date"
              type="date"
              value={values.alternate_date ?? ''}
              onChange={(event) => change('alternate_date', event.target.value || null)}
              onBlur={() => blur('alternate_date')}
            />
          )}
        </FormField>
      </div>
      <div className="grid gap-5 sm:grid-cols-3 sm:gap-4">
        <FormField label="Start time" error={errors.start_time} required>
          {(field) => (
            <Input
              {...field}
              name="start_time"
              type="time"
              value={values.start_time}
              onChange={(event) => change('start_time', event.target.value)}
              onBlur={() => blur('start_time')}
            />
          )}
        </FormField>
        <FormField label="Hours" error={errors.duration_hours} required>
          {(field) => (
            <Select
              {...field}
              name="duration_hours"
              options={[
                { value: '', label: 'Choose' },
                ...DURATIONS.map((hours) => ({ value: String(hours), label: `${hours} hour${hours === 1 ? '' : 's'}` })),
              ]}
              value={values.duration_hours ? String(values.duration_hours) : ''}
              onChange={(event) => change('duration_hours', event.target.value ? Number(event.target.value) : null)}
              onBlur={() => blur('duration_hours')}
            />
          )}
        </FormField>
        <FormField label="How many people" error={errors.party_size} required>
          {(field) => (
            <Input
              {...field}
              name="party_size"
              type="number"
              inputMode="numeric"
              min={1}
              max={200}
              value={values.party_size ?? ''}
              onChange={(event) => change('party_size', event.target.value ? Number(event.target.value) : null)}
              onBlur={() => blur('party_size')}
            />
          )}
        </FormField>
      </div>
      <FormField label="Anything else we should know" error={errors.notes}>
        {(field) => (
          <Textarea
            {...field}
            name="notes"
            rows={5}
            maxLength={3000}
            value={values.notes}
            onChange={(event) => change('notes', event.target.value)}
            onBlur={() => blur('notes')}
          />
        )}
      </FormField>
      {values.type === 'photoshoot' && (
        <div className="rounded-field bg-blush p-4">
          <Checkbox
            name="photoshoot_acknowledged"
            label={PHOTOSHOOT_PROMISE}
            required
            checked={values.photoshoot_acknowledged}
            error={errors.photoshoot_acknowledged}
            onChange={(event) => change('photoshoot_acknowledged', event.target.checked)}
            onBlur={() => blur('photoshoot_acknowledged')}
          />
        </div>
      )}

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
            onChange={(event) => change('website', event.target.value)}
          />
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <Button type="submit" size="lg" disabled={submitting} aria-busy={submitting}>
          {submitting ? 'Sending' : 'Send request'}
        </Button>
        <p className="text-[0.8125rem] text-fg-muted">
          We only use your details to reply.{' '}
          <Link to="/privacy" className="underline underline-offset-4 hover:text-fg">
            Privacy
          </Link>
        </p>
      </div>
    </form>
  )
}

/** Rentals (no design: the spaces as a card, the inquiry form laid out like Contact). */
export function RentalsPage() {
  useDocumentMeta({
    title: 'Rentals',
    description: 'Rent the space for private sessions, workshops, photoshoots and group events.',
  })
  const copy = usePageContent('rentals')
  const auth = useAuth()

  return (
    <>
      <PageHero copy={copy} image="about-hero.webp" placeholder="warm" />

      <Section aria-labelledby="spaces">
        <div className="grid gap-8 lg:grid-cols-2 lg:gap-24">
          <CopyHeading copy={copy} prefix="spaces" id="spaces" />
          <Card className="p-6 lg:p-8">
            <Copy copy={copy} k="uses.title" as="h3" className="text-xl text-fg lg:text-card-title" />
            <CopyList copy={copy} prefix="uses" />
            <Copy copy={copy} k="included.title" as="h3" className="mt-8 text-xl text-fg lg:text-card-title" />
            <CopyList copy={copy} prefix="included" />
          </Card>
        </div>
      </Section>

      <Section rule aria-labelledby="inquire">
        <div className="grid gap-8 lg:grid-cols-2 lg:gap-24">
          <CopyHeading copy={copy} prefix="form" id="inquire" />
          <div className="w-full lg:max-w-[520px]">
            {auth.status === 'loading' ? (
              <LoadingState label="Loading the form" />
            ) : (
              <RentalInquiryForm key={auth.user?.display_name ?? 'signed-out'} />
            )}
          </div>
        </div>
      </Section>
    </>
  )
}

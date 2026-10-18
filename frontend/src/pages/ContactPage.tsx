import { CircleCheck, Mail, MapPin, ShieldAlert } from 'lucide-react'
import { useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { PageHero } from '@/components/content/PageHero'
import { ErrorState, LoadingState } from '@/components/content/States'
import { useSiteSettings } from '@/components/layout/siteSettingsContext'
import { Button, Card, FormField, Input, Section, Select, Textarea, useToast } from '@/components/ui'
import { api, ApiError, type ContactPayload, type FieldErrors } from '@/lib/api'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { EMPTY_FORM, FIELDS, TOPIC_OPTIONS, validateAll, validateField, type ContactField } from './contactValidation'

function ContactDetails() {
  const settings = useSiteSettings()
  if (settings.status === 'loading') return <LoadingState label="Loading contact details" />
  if (settings.status === 'error') return <ErrorState title="Contact details did not load" onRetry={settings.retry} />
  const { address_text, contact_email } = settings.data
  return (
    <ul className="space-y-6">
      {contact_email && (
        <li className="flex gap-4">
          <Mail aria-hidden="true" className="mt-1 size-5 shrink-0 text-highlight" strokeWidth={1.5} />
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-fg-subtle">Email</p>
            <a href={`mailto:${contact_email}`} className="mt-1 inline-block text-lg text-fg underline-offset-4 hover:underline">
              {contact_email}
            </a>
          </div>
        </li>
      )}
      {address_text && (
        <li className="flex gap-4">
          <MapPin aria-hidden="true" className="mt-1 size-5 shrink-0 text-highlight" strokeWidth={1.5} />
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-fg-subtle">Address</p>
            <p className="mt-1 whitespace-pre-line text-lg text-fg">{address_text}</p>
          </div>
        </li>
      )}
    </ul>
  )
}

export function ContactPage() {
  useDocumentMeta({
    title: 'Contact',
    description: 'Ask a question, plan a visit, offer to volunteer or raise a concern in confidence.',
  })
  const toast = useToast()
  const [values, setValues] = useState<ContactPayload>(EMPTY_FORM)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [touched, setTouched] = useState<Partial<Record<ContactField, boolean>>>({})
  const [submitting, setSubmitting] = useState(false)
  const [sent, setSent] = useState(false)
  const formRef = useRef<HTMLFormElement>(null)
  const successRef = useRef<HTMLHeadingElement>(null)

  function change(field: keyof ContactPayload, value: string) {
    const next = { ...values, [field]: value }
    setValues(next)
    if (field !== 'website' && touched[field]) {
      setErrors((current) => ({ ...current, [field]: validateField(field, next) }))
    }
  }

  function blur(field: ContactField) {
    setTouched((current) => ({ ...current, [field]: true }))
    setErrors((current) => ({ ...current, [field]: validateField(field, values) }))
  }

  function focusFirstError(fieldErrors: FieldErrors) {
    const first = FIELDS.find((field) => fieldErrors[field])
    if (first) formRef.current?.querySelector<HTMLElement>(`[name="${first}"]`)?.focus()
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const clientErrors = validateAll(values)
    setTouched({ name: true, email: true, phone: true, topic: true, message: true })
    setErrors(clientErrors)
    if (Object.keys(clientErrors).length > 0) {
      focusFirstError(clientErrors)
      return
    }

    setSubmitting(true)
    try {
      await api.sendContactMessage(values)
      setSent(true)
      setValues(EMPTY_FORM)
      setTouched({})
      requestAnimationFrame(() => successRef.current?.focus())
    } catch (error) {
      if (error instanceof ApiError && Object.keys(error.fieldErrors).length > 0) {
        setErrors(error.fieldErrors)
        focusFirstError(error.fieldErrors)
        toast.show({ tone: 'error', title: 'Please check the highlighted fields.' })
      } else if (error instanceof ApiError && error.isRateLimited) {
        toast.show({ tone: 'error', title: 'Too many messages', message: 'Please wait a while before sending another.' })
      } else {
        toast.show({
          tone: 'error',
          title: 'Your message was not sent',
          message: error instanceof Error ? error.message : 'Please try again in a moment.',
        })
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <PageHero
        eyebrow="Contact"
        title="We would love to hear from you."
        lede="Questions, first-visit nerves, volunteering, or something that needs our attention. A real person reads every message."
        image="contact-hero.webp"
        placeholder="silk"
      />

      <Section>
        <div className="grid gap-12 lg:grid-cols-[1.5fr_1fr] lg:gap-16">
          <Card className="p-6 sm:p-10">
            {sent ? (
              <div className="py-6" role="status">
                <CircleCheck aria-hidden="true" className="size-10 text-success" strokeWidth={1.5} />
                <h2 ref={successRef} tabIndex={-1} className="mt-6 text-4xl text-fg focus:outline-none">
                  Thank you. Your message is with us.
                </h2>
                <p className="mt-4 max-w-lg leading-relaxed text-fg-muted">
                  A volunteer will reply to the email address you gave, usually within a few days. Reports of concern are
                  read first.
                </p>
                <Button variant="ghost" className="mt-8" onClick={() => setSent(false)}>
                  Send another message
                </Button>
              </div>
            ) : (
              <form ref={formRef} noValidate onSubmit={submit} className="flex flex-col gap-6" aria-label="Contact form">
                <div className="grid gap-6 sm:grid-cols-2">
                  <FormField label="Name or display name" error={errors.name} required>
                    {(field) => (
                      <Input
                        {...field}
                        name="name"
                        autoComplete="nickname"
                        value={values.name}
                        onChange={(event) => change('name', event.target.value)}
                        onBlur={() => blur('name')}
                      />
                    )}
                  </FormField>
                  <FormField label="Email" error={errors.email} required>
                    {(field) => (
                      <Input
                        {...field}
                        name="email"
                        type="email"
                        autoComplete="email"
                        inputMode="email"
                        value={values.email}
                        onChange={(event) => change('email', event.target.value)}
                        onBlur={() => blur('email')}
                      />
                    )}
                  </FormField>
                </div>
                <div className="grid gap-6 sm:grid-cols-2">
                  <FormField label="Phone" hint="Only if you would like a call back." error={errors.phone}>
                    {(field) => (
                      <Input
                        {...field}
                        name="phone"
                        type="tel"
                        autoComplete="tel"
                        value={values.phone}
                        onChange={(event) => change('phone', event.target.value)}
                        onBlur={() => blur('phone')}
                      />
                    )}
                  </FormField>
                  <FormField label="Topic" error={errors.topic} required>
                    {(field) => (
                      <Select
                        {...field}
                        name="topic"
                        options={TOPIC_OPTIONS}
                        value={values.topic}
                        onChange={(event) => change('topic', event.target.value)}
                        onBlur={() => blur('topic')}
                      />
                    )}
                  </FormField>
                </div>
                {values.topic === 'concern' && (
                  <div className="flex gap-3 rounded-xl border border-rose/40 bg-primary-deep/40 p-4 text-sm leading-relaxed text-fg-muted">
                    <ShieldAlert aria-hidden="true" className="size-5 shrink-0 text-rose" />
                    <p>
                      Concerns go to a small safety team and are marked as a priority. Share as much or as little as you
                      are comfortable with. If someone is in immediate danger, call 911.
                    </p>
                  </div>
                )}
                <FormField label="Message" error={errors.message} required>
                  {(field) => (
                    <Textarea
                      {...field}
                      name="message"
                      value={values.message}
                      maxLength={5000}
                      onChange={(event) => change('message', event.target.value)}
                      onBlur={() => blur('message')}
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
                      onChange={(event) => change('website', event.target.value)}
                    />
                  </label>
                </div>

                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <p className="text-sm text-fg-subtle">
                    We use your details only to reply.{' '}
                    <Link to="/privacy" className="underline underline-offset-4 hover:text-fg">
                      Privacy
                    </Link>
                  </p>
                  <Button type="submit" size="lg" disabled={submitting} aria-busy={submitting}>
                    {submitting ? 'Sending' : 'Send message'}
                  </Button>
                </div>
              </form>
            )}
          </Card>

          <aside aria-label="Contact details" className="lg:pt-4">
            <h2 className="text-3xl text-fg">Other ways to reach us</h2>
            <div className="mt-8">
              <ContactDetails />
            </div>
            <p className="mt-10 border-t border-border pt-6 text-sm leading-relaxed text-fg-muted">
              Messages are stored privately and read only by the volunteers who answer them. Email notifications to our
              team never include what you wrote.
            </p>
          </aside>
        </div>
      </Section>
    </>
  )
}

import { ShieldAlert } from 'lucide-react'
import { useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { Copy, CopySkeleton } from '@/components/content/Copy'
import { ErrorState } from '@/components/content/States'
import { useSiteSettings } from '@/components/layout/siteSettingsContext'
import { Button, FormField, Input, Section, Select, Textarea, useToast } from '@/components/ui'
import { api, ApiError, type ContactPayload, type FieldErrors } from '@/lib/api'
import { cn } from '@/lib/cn'
import { usePageContent } from '@/lib/pageContent'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { EMPTY_FORM, FIELDS, TOPIC_OPTIONS, validateAll, validateField, type ContactField } from './contactValidation'
import { SENT_ACTION, SentPanel } from './SentPanel'

/** The club's contact address, from the site settings, as a rose link. */
function ContactEmail() {
  const settings = useSiteSettings()
  if (settings.status === 'loading') return <CopySkeleton className="w-48" />
  if (settings.status === 'error') return <ErrorState title="Contact details did not load" onRetry={settings.retry} />
  const { contact_email } = settings.data
  if (!contact_email) return null
  return (
    <a href={`mailto:${contact_email}`} className="self-start font-semibold text-link hover:text-primary-hover">
      {contact_email}
    </a>
  )
}

/**
 * Contact (design: "Contact · desktop" and "Contact · phone (success)"): the title, lead and
 * address on the left, the form on the right, and a blush confirmation once it is sent.
 */
export function ContactPage() {
  useDocumentMeta({
    title: 'Contact',
    description: 'Ask a question, plan a visit, offer to volunteer or raise a concern in confidence.',
  })
  const toast = useToast()
  const copy = usePageContent('contact')
  const [values, setValues] = useState<ContactPayload>(EMPTY_FORM)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [touched, setTouched] = useState<Partial<Record<ContactField, boolean>>>({})
  const [submitting, setSubmitting] = useState(false)
  // What the visitor typed, kept only to thank them by name; never sent anywhere else.
  const [sent, setSent] = useState<{ name: string; email: string; concern: boolean } | null>(null)
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
      setSent({ name: values.name.trim(), email: values.email.trim(), concern: values.topic === 'concern' })
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
    <Section spacing="none" className="pb-12 pt-7 lg:py-16">
      <div className="grid gap-6 lg:grid-cols-2 lg:gap-24">
        <div className="flex flex-col gap-3 lg:gap-4">
          <h1 className="text-[2.25rem] font-light leading-[1.05] text-fg lg:text-h1">
            {copy.status === 'loading' ? (
              <>
                <span className="sr-only">Contact</span>
                <CopySkeleton />
              </>
            ) : (
              <Copy copy={copy} k="hero.title" as="span" />
            )}
          </h1>
          <div className={cn('flex flex-col gap-3 lg:gap-4', sent && 'hidden lg:flex')}>
            <Copy copy={copy} k="hero.lede" lines={2} className="max-w-[440px] text-fg-muted lg:text-lead" />
            <ContactEmail />
          </div>
        </div>

        <div className="w-full lg:max-w-[520px]">
          {sent ? (
            <SentPanel
              headingRef={successRef}
              title={`Thanks, ${sent.name}. We got it.`}
              actions={
                <>
                  <Link to="/" className={SENT_ACTION}>
                    Back to home
                  </Link>
                  <button type="button" onClick={() => setSent(null)} className="min-h-6 text-sm font-semibold text-fg-muted-tint hover:text-fg">
                    Send another message
                  </button>
                </>
              }
            >
              A volunteer will reply to {sent.email} within a few days.
              {sent.concern && ' Reports of concern are read first.'}
            </SentPanel>
          ) : (
            <form ref={formRef} noValidate onSubmit={submit} className="flex flex-col gap-5" aria-label="Contact form">
              <div className="grid gap-5 sm:grid-cols-2 sm:gap-4">
                <FormField label="Name" error={errors.name} required>
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
              <div className="grid gap-5 sm:grid-cols-2 sm:gap-4">
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
              </div>
              {values.topic === 'concern' && (
                <div className="flex gap-3 rounded-field bg-blush p-4 text-sm text-fg-muted-tint">
                  <ShieldAlert aria-hidden="true" className="size-5 shrink-0 text-link" />
                  <Copy copy={copy} k="concern" as="div" lines={2} />
                </div>
              )}
              <FormField label="Message" error={errors.message} required>
                {(field) => (
                  <Textarea
                    {...field}
                    name="message"
                    rows={4}
                    maxLength={5000}
                    value={values.message}
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

              <div className="flex flex-wrap items-center gap-4">
                <Button type="submit" size="lg" disabled={submitting} aria-busy={submitting}>
                  {submitting ? 'Sending' : 'Send'}
                </Button>
                <p className="text-[0.8125rem] text-fg-muted">We only use your email to reply.</p>
              </div>
            </form>
          )}
        </div>
      </div>
    </Section>
  )
}

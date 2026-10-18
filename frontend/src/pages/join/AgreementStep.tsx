import { ArrowLeft, ScrollText } from 'lucide-react'
import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { RICH_TEXT } from '@/components/content/richText'
import { Badge, Button, FormField, Input } from '@/components/ui'
import { cn } from '@/lib/cn'
import type { Agreement } from '@/lib/membershipApi'

interface AgreementStepProps {
  agreement: Agreement
  notice?: string
  onBack: () => void
  onSigned: (typedName: string) => void
}

/** Read to the end, tick the box, type a full name. Only staff ever see that name. */
export function AgreementStep({ agreement, notice, onBack, onSigned }: AgreementStepProps) {
  const [read, setRead] = useState(false)
  const [agreed, setAgreed] = useState(false)
  const [name, setName] = useState('')
  const [error, setError] = useState<string>()
  const scrollRef = useRef<HTMLDivElement>(null)
  const endRef = useRef<HTMLDivElement>(null)
  const checkboxId = useId()

  useEffect(() => {
    // Also covers an agreement short enough to fit without scrolling.
    const root = scrollRef.current
    const end = endRef.current
    if (!root || !end || typeof IntersectionObserver === 'undefined') return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) setRead(true)
      },
      { root, threshold: 1 },
    )
    observer.observe(end)
    return () => observer.disconnect()
  }, [])

  function onScroll() {
    const el = scrollRef.current
    if (el && el.scrollTop + el.clientHeight >= el.scrollHeight - 16) setRead(true)
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const typed = name.trim().replace(/\s+/g, ' ')
    if (typed.length < 2) {
      setError('Type your full name to sign.')
      return
    }
    onSigned(typed)
  }

  const ready = read && agreed && name.trim().length >= 2

  return (
    <form noValidate onSubmit={submit} aria-labelledby="agreement-heading" className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="agreement-heading" className="flex items-center gap-3 text-3xl text-fg">
          <ScrollText aria-hidden="true" className="size-6 text-highlight" />
          {agreement.title}
        </h2>
        {agreement.is_placeholder && <Badge tone="rose">Placeholder text</Badge>}
      </div>
      {notice && (
        <p role="alert" className="rounded-xl border border-highlight/40 bg-primary-deep/40 p-4 text-sm text-fg">
          {notice}
        </p>
      )}
      <div
        ref={scrollRef}
        onScroll={onScroll}
        tabIndex={0}
        role="region"
        aria-label="Agreement text"
        className="max-h-[50svh] overflow-y-auto rounded-2xl border border-border bg-surface-sunken p-5 focus-visible:outline-2 focus-visible:outline-highlight sm:p-7"
      >
        <div className={RICH_TEXT} dangerouslySetInnerHTML={{ __html: agreement.body }} />
        <div ref={endRef} className="h-px" />
      </div>
      <p className={cn('text-sm', read ? 'text-success' : 'text-fg-subtle')} aria-live="polite">
        {read ? 'You have reached the end.' : 'Scroll to the end to continue.'}
      </p>

      <div className="flex items-start gap-3">
        <input
          id={checkboxId}
          type="checkbox"
          checked={agreed}
          disabled={!read}
          onChange={(event) => setAgreed(event.target.checked)}
          className="mt-1 size-5 accent-[var(--color-primary)] disabled:opacity-40"
        />
        <label htmlFor={checkboxId} className={cn('text-fg', !read && 'text-fg-subtle')}>
          I have read and agree
        </label>
      </div>

      <FormField
        label="Your full name"
        hint="Typing your name signs the agreement. Only staff can see it, and it is never shown to other members."
        error={error}
        required
      >
        {(field) => (
          <Input
            {...field}
            name="typed_name"
            autoComplete="name"
            maxLength={200}
            value={name}
            disabled={!agreed}
            onChange={(e) => {
              setName(e.target.value)
              setError(undefined)
            }}
          />
        )}
      </FormField>

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft aria-hidden="true" className="size-4" />
          Back
        </Button>
        <Button type="submit" size="lg" disabled={!ready}>
          Sign and continue
        </Button>
      </div>
    </form>
  )
}

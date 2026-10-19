import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { RICH_TEXT } from '@/components/content/richText'
import { Button, CheckboxBox, FormField, Input } from '@/components/ui'
import { cn } from '@/lib/cn'
import type { Agreement, Tier } from '@/lib/membershipApi'
import { BACK_BUTTON } from './joinParts'
import { JoinProgress, TierSummary } from './JoinSteps'

interface AgreementStepProps {
  agreement: Agreement
  tier: Tier
  notice?: string
  /** True while signing finishes the join (a free tier has no payment step). */
  busy?: boolean
  submitLabel?: string
  onBack: () => void
  onSigned: (typedName: string) => void
}

/**
 * Join step 2 (design: "Join step 2"): read to the end, tick the box, type a full name.
 * Only staff ever see that name.
 */
export function AgreementStep({ agreement, tier, notice, busy = false, submitLabel = 'Agree and continue', onBack, onSigned }: AgreementStepProps) {
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
    <form noValidate onSubmit={submit} aria-labelledby="agreement-heading" className="grid gap-5 lg:grid-cols-[420px_1fr] lg:gap-20">
      <div className="flex flex-col gap-3 lg:gap-4">
        <JoinProgress current={2} caption="Agreement" />
        <h1 id="agreement-heading" className="text-[2rem] font-light leading-[1.05] text-fg lg:text-h2-lg">
          {agreement.title}
        </h1>
        <p className="hidden text-base text-fg-muted lg:block">Please read the whole thing. Hosts will hold you to it.</p>
        <div className="hidden lg:mt-2 lg:block">
          <TierSummary tier={tier} />
        </div>
      </div>

      <div className="flex min-w-0 flex-col gap-4 lg:gap-5">
        {notice && (
          <p role="alert" className="rounded-card bg-blush p-4 text-sm text-fg">
            {notice}
          </p>
        )}
        <div className="relative">
          <div
            ref={scrollRef}
            onScroll={onScroll}
            tabIndex={0}
            role="region"
            aria-label="Agreement text"
            className="h-[300px] overflow-y-auto rounded-card border border-border p-5 text-sm focus-visible:outline-2 focus-visible:outline-link lg:h-[360px] lg:px-8 lg:py-7 lg:text-[0.9375rem]"
          >
            <div className={cn(RICH_TEXT, 'space-y-4 [&_strong]:font-semibold')} dangerouslySetInnerHTML={{ __html: agreement.body }} />
            <div ref={endRef} className="h-px" />
          </div>
          {/* The fade says "there is more"; it goes once the end has been reached. */}
          <div
            aria-hidden="true"
            className={cn(
              'pointer-events-none absolute inset-x-px bottom-px h-[70px] rounded-b-card bg-linear-to-b from-transparent to-canvas transition-opacity lg:h-20',
              read && 'opacity-0',
            )}
          />
        </div>
        <p className={cn('sr-only text-[0.8125rem] lg:not-sr-only', read ? 'text-link' : 'text-fg-muted')} aria-live="polite">
          {read ? 'You have reached the end.' : 'Scroll to the end to enable the checkbox.'}
        </p>

        <div className="flex items-start gap-3">
          <CheckboxBox id={checkboxId} checked={agreed} disabled={!read} onChange={(event) => setAgreed(event.target.checked)} className="mt-px lg:mt-0.5" />
          <label htmlFor={checkboxId} className={cn('text-sm lg:text-[0.9375rem]', read ? 'text-fg' : 'text-fg-muted')}>
            I have read the agreement and I agree to it.
          </label>
        </div>

        <div className="lg:max-w-[400px]">
          <FormField
            label="Type your full name to sign"
            hint="Only staff can see it. It is never shown to other members."
            error={error}
            required
            optionalLabel=""
          >
            {(field) => (
              <Input
                {...field}
                name="typed_name"
                autoComplete="name"
                maxLength={200}
                placeholder="Your name"
                value={name}
                disabled={!agreed}
                className="font-display text-lg italic"
                onChange={(e) => {
                  setName(e.target.value)
                  setError(undefined)
                }}
              />
            )}
          </FormField>
        </div>

        <div className="mt-1 flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
          <Button type="submit" size="lg" disabled={!ready || busy} aria-busy={busy}>
            {busy ? 'Working' : submitLabel}
          </Button>
          <button type="button" onClick={onBack} disabled={busy} className={cn(BACK_BUTTON, 'self-center sm:self-auto')}>
            Back
          </button>
        </div>
      </div>
    </form>
  )
}

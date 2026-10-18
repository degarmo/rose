import { CalendarHeart, Check, GraduationCap, KeyRound, Lock, UserPlus } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router'
import { PageHero } from '@/components/content/PageHero'
import { Reveal } from '@/components/content/Reveal'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { Badge, Button, ButtonLink, Card, Section, SectionHeading, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import {
  goTo,
  isOpen,
  membershipApi,
  type JoinOptions,
  type MyMembership,
  priceLabel,
  type PaymentMethod,
  type Tier,
} from '@/lib/membershipApi'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { AgreementStep } from './AgreementStep'
import { JoinConfirmation } from './JoinConfirmation'

const BENEFITS = [
  {
    icon: CalendarHeart,
    title: 'Members-only evenings',
    body: 'Seasonal gatherings, member nights and community meetings, with a say in how the house is run.',
  },
  {
    icon: GraduationCap,
    title: 'Members-only classes',
    body: 'Smaller, deeper sessions and mentorship circles that build on the public education program.',
  },
  {
    icon: KeyRound,
    title: 'The member community',
    body: 'A private feed for members who choose to join it. Off unless you turn it on.',
  },
  {
    icon: Lock,
    title: 'Private by design',
    body: 'You are known by a display name you choose. Payment records are kept apart from everything else.',
  },
]

type Step =
  | { name: 'tiers' }
  | { name: 'agreement'; tier: Tier; notice?: string }
  | { name: 'method'; tier: Tier; typedName: string }
  | { name: 'done'; membership: MyMembership }

const STEPS = ['Choose', 'Agreement', 'Payment'] as const

function Stepper({ current }: { current: number }) {
  return (
    <ol className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm" aria-label="Steps">
      {STEPS.map((label, index) => (
        <li
          key={label}
          aria-current={index === current ? 'step' : undefined}
          className={cn('flex items-center gap-2', index === current ? 'text-fg' : index < current ? 'text-fg-muted' : 'text-fg-subtle')}
        >
          <span
            aria-hidden="true"
            className={cn(
              'inline-flex size-7 items-center justify-center rounded-full border text-xs',
              index <= current ? 'border-highlight text-highlight' : 'border-border-strong',
            )}
          >
            {index < current ? <Check className="size-3.5" /> : index + 1}
          </span>
          {label}
        </li>
      ))}
    </ol>
  )
}

function TierCards({ tiers, canChoose, onChoose }: { tiers: Tier[]; canChoose: boolean; onChoose: (tier: Tier) => void }) {
  return (
    <ul className="grid gap-6 md:grid-cols-3">
      {tiers.map((tier) => (
        <li key={tier.slug}>
          <Card className="h-full p-6 sm:p-7">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-2xl text-fg">{tier.name}</h3>
              {tier.is_placeholder && <Badge tone="rose">Placeholder price</Badge>}
            </div>
            <p className="mt-2 font-display text-3xl text-accent">{priceLabel(tier)}</p>
            {tier.description && <p className="mt-3 text-sm leading-relaxed text-fg-muted">{tier.description}</p>}
            {tier.benefits.length > 0 && (
              <ul className="mt-5 flex flex-col gap-2 text-sm text-fg-muted">
                {tier.benefits.map((benefit) => (
                  <li key={benefit} className="flex gap-2">
                    <Check aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-highlight" />
                    {benefit}
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-auto pt-7">
              <Button className="w-full" size="lg" disabled={!canChoose} onClick={() => onChoose(tier)} aria-label={`Choose ${tier.name}`}>
                Choose
              </Button>
            </div>
          </Card>
        </li>
      ))}
    </ul>
  )
}

function MethodStep({
  tier,
  methods,
  busy,
  onBack,
  onSubmit,
}: {
  tier: Tier
  methods: PaymentMethod[]
  busy: boolean
  onBack: () => void
  onSubmit: (method: string) => void
}) {
  const [method, setMethod] = useState(methods[0]?.key ?? 'manual')
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit(method)
      }}
      aria-labelledby="method-heading"
      className="flex flex-col gap-6"
    >
      <h2 id="method-heading" className="text-3xl text-fg">
        How would you like to pay?
      </h2>
      <p className="text-fg-muted">
        {tier.name}, {priceLabel(tier)}. Your bank statement shows a neutral name and the word &ldquo;Membership&rdquo;.
      </p>
      <fieldset className="flex flex-col gap-3">
        <legend className="sr-only">Payment method</legend>
        {methods.map((option) => (
          <label
            key={option.key}
            className={cn(
              'flex cursor-pointer items-start gap-4 rounded-2xl border p-5 transition-colors',
              method === option.key ? 'border-highlight bg-surface-raised' : 'border-border bg-surface hover:border-border-strong',
            )}
          >
            <input
              type="radio"
              name="method"
              value={option.key}
              checked={method === option.key}
              onChange={() => setMethod(option.key)}
              className="mt-1 size-4 accent-[var(--color-primary)]"
            />
            <span>
              <span className="block font-medium text-fg">{option.label}</span>
              <span className="mt-1 block text-sm text-fg-muted">
                {option.online
                  ? 'Pay now on a secure checkout page. Your membership starts once payment is confirmed and staff have seen your photo ID once.'
                  : 'Get a reference code now. Bring it, your payment and a valid photo ID on your first visit, and staff will start your membership at the door.'}
              </span>
            </span>
          </label>
        ))}
      </fieldset>
      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <Button variant="ghost" onClick={onBack} disabled={busy}>
          Back
        </Button>
        <Button type="submit" size="lg" disabled={busy} aria-busy={busy}>
          {busy ? 'Working' : methods.find((m) => m.key === method)?.online ? 'Continue to checkout' : 'Get my reference code'}
        </Button>
      </div>
    </form>
  )
}

function ExistingMembership({ membership }: { membership: MyMembership }) {
  return (
    <Card className="p-6 sm:p-8">
      <h2 className="text-3xl text-fg">You already have a membership</h2>
      <p className="mt-3 text-fg-muted">
        {membership.tier.name} &middot; {membership.status_label}. Your code, payments and renewal are on your account page.
      </p>
      <ButtonLink to="/account#membership" size="lg" className="mt-6 self-start">
        See my membership
      </ButtonLink>
    </Card>
  )
}

function SignInFirst() {
  const next = encodeURIComponent('/join')
  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-border bg-surface p-5 sm:flex-row sm:items-center">
      <p className="flex-1 text-fg-muted">Joining takes a free account, so your membership has somewhere private to live.</p>
      <div className="flex flex-col gap-3 sm:flex-row">
        <ButtonLink to={`/account/register?next=${next}`}>
          <UserPlus aria-hidden="true" className="size-4" />
          Create an account
        </ButtonLink>
        <ButtonLink to={`/account/login?next=${next}`} variant="ghost">
          Log in
        </ButtonLink>
      </div>
    </div>
  )
}

function JoinFlow({ tiers, options, existing, reloadOptions }: { tiers: Tier[]; options: JoinOptions; existing: MyMembership | null; reloadOptions: () => void }) {
  const auth = useAuth()
  const toast = useToast()
  const [step, setStep] = useState<Step>({ name: 'tiers' })
  const [busy, setBusy] = useState(false)
  const top = useRef<HTMLDivElement>(null)
  const agreement = options.agreement

  useEffect(() => {
    // On a phone the next step would otherwise start above the screen.
    if (step.name !== 'tiers') top.current?.scrollIntoView?.({ block: 'start' })
  }, [step.name])

  if (step.name === 'done') {
    return (
      <div ref={top} className="scroll-mt-24">
        <JoinConfirmation membership={step.membership} />
      </div>
    )
  }
  if (isOpen(existing)) return <ExistingMembership membership={existing} />
  if (!agreement || tiers.length === 0) {
    return (
      <EmptyState
        title="Joining online is not open yet"
        message="Start with a newcomer orientation on any Thursday and our hosts will walk you through membership in person."
      />
    )
  }

  async function join(tier: Tier, typedName: string, method: string) {
    if (!agreement) return
    setBusy(true)
    try {
      const result = await membershipApi.join({ tier: tier.slug, agreement_version: agreement.version, typed_name: typedName, method })
      await auth.refresh()
      if (result.redirect_url) {
        goTo(result.redirect_url)
        return
      }
      if (result.membership) setStep({ name: 'done', membership: result.membership })
    } catch (error) {
      if (error instanceof ApiError && error.fieldErrors.code === 'agreement_changed') {
        reloadOptions()
        setStep({ name: 'agreement', tier, notice: 'The agreement was just updated. Please read the new version.' })
      } else {
        toast.show({ tone: 'error', title: 'You have not joined yet', message: error instanceof Error ? error.message : 'Please try again.' })
      }
    } finally {
      setBusy(false)
    }
  }

  const current = step.name === 'tiers' ? 0 : step.name === 'agreement' ? 1 : 2
  const verified = Boolean(auth.user?.email_verified)

  return (
    <div ref={top} className="flex scroll-mt-24 flex-col gap-8">
      <Stepper current={current} />
      {step.name === 'tiers' && (
        <>
          {auth.status === 'ready' && !auth.user && <SignInFirst />}
          {auth.user && !auth.user.email_verified && (
            <p role="status" className="rounded-2xl border border-highlight/40 bg-primary-deep/40 p-5 text-fg-muted">
              Confirm your email first. Open the link we sent to {auth.user.email}, then come back here.
            </p>
          )}
          <TierCards tiers={tiers} canChoose={verified} onChoose={(tier) => setStep({ name: 'agreement', tier })} />
        </>
      )}
      {step.name === 'agreement' && (
        <AgreementStep
          key={agreement.version}
          agreement={agreement}
          notice={step.notice}
          onBack={() => setStep({ name: 'tiers' })}
          onSigned={(typedName) => setStep({ name: 'method', tier: step.tier, typedName })}
        />
      )}
      {step.name === 'method' && (
        <MethodStep
          tier={step.tier}
          methods={options.methods}
          busy={busy}
          onBack={() => setStep({ name: 'agreement', tier: step.tier })}
          onSubmit={(method) => void join(step.tier, step.typedName, method)}
        />
      )}
    </div>
  )
}

export function JoinPage() {
  useDocumentMeta({ title: 'Join', description: 'What membership includes and how to become a member.' })
  const auth = useAuth()
  const [params] = useSearchParams()
  const cancelled = params.get('cancelled') === '1'
  const tiers = useAsync(() => membershipApi.tiers(), 'tiers')
  const options = useAsync(() => membershipApi.options(), 'join-options')
  const signedIn = auth.user ? auth.user.display_name : ''
  const me = useAsync(() => (signedIn ? membershipApi.me() : Promise.resolve(null)), `me:${signedIn}`)

  let flow
  if (tiers.status === 'loading' || options.status === 'loading' || (signedIn && me.status === 'loading') || auth.status === 'loading') {
    flow = <LoadingState label="Loading membership options" />
  } else if (tiers.status === 'error' || options.status === 'error' || me.status === 'error') {
    flow = (
      <ErrorState
        title="Membership options did not load"
        onRetry={() => {
          tiers.retry()
          options.retry()
          me.retry()
        }}
      />
    )
  } else {
    flow = (
      <JoinFlow
        key={signedIn}
        tiers={tiers.data}
        options={options.data}
        existing={me.data?.membership ?? null}
        reloadOptions={options.retry}
      />
    )
  }

  return (
    <>
      <PageHero
        eyebrow="Membership"
        title="Become part of the house."
        lede="Membership supports a volunteer-run nonprofit and opens members' evenings, members-only classes and the member community."
        image="join-hero.webp"
        placeholder="rose"
      />

      <Section width="narrow" aria-labelledby="join-heading">
        <h2 id="join-heading" className="mb-10 text-4xl text-fg sm:text-5xl">
          Join
        </h2>
        {cancelled && (
          <p role="status" className="mb-8 rounded-2xl border border-border bg-surface p-5 text-fg-muted">
            Checkout was cancelled and nothing was charged. You can pick up where you left off below.
          </p>
        )}
        {flow}
      </Section>

      <Section tone="surface" aria-labelledby="benefits">
        <SectionHeading id="benefits" eyebrow="What membership includes" title="More of what you love about the house." />
        <ul className="mt-14 grid gap-6 sm:grid-cols-2">
          {BENEFITS.map((benefit, index) => {
            const Icon = benefit.icon
            return (
              <Reveal as="li" key={benefit.title} delay={(index % 2) as 0 | 1}>
                <Card className="h-full p-8">
                  <Icon aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
                  <h3 className="mt-6 text-2xl text-fg">{benefit.title}</h3>
                  <p className="mt-3 leading-relaxed text-fg-muted">{benefit.body}</p>
                </Card>
              </Reveal>
            )
          })}
        </ul>
      </Section>
    </>
  )
}

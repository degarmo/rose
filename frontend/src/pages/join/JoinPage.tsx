import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router'
import { Copy, CopyHeading, CopySkeleton } from '@/components/content/Copy'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { TierCard } from '@/components/membership/TierCard'
import { Button, ButtonLink, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { formatMoney } from '@/lib/format'
import {
  billingLabel,
  goTo,
  isOpen,
  membershipApi,
  membershipTiers,
  type JoinOptions,
  type MyMembership,
  type PaymentMethod,
  type Tier,
} from '@/lib/membershipApi'
import { usePageContent, type PageCopy } from '@/lib/pageContent'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { AgreementStep } from './AgreementStep'
import { JoinConfirmation } from './JoinConfirmation'
import { BACK_BUTTON, JOIN_FRAME } from './joinParts'
import { JoinProgress, JoinSteps, TierSummary } from './JoinSteps'

type Step =
  | { name: 'tiers' }
  | { name: 'agreement'; tier: Tier; notice?: string }
  | { name: 'method'; tier: Tier; typedName: string }
  | { name: 'done'; membership: MyMembership }

type Access = 'anonymous' | 'unverified' | 'verified'

/** Signed out, a tier's button leads to a free account and back here with the tier chosen. */
function registerFor(tier: Tier) {
  return `/account/register?next=${encodeURIComponent(`/join?tier=${tier.slug}`)}`
}

function ChooseButton({ tier, access, onChoose, className }: { tier: Tier; access: Access; onChoose: (tier: Tier) => void; className?: string }) {
  const variant = tier.is_featured ? 'primary' : 'outline'
  if (access === 'anonymous') {
    return (
      <ButtonLink to={registerFor(tier)} size="lg" variant={variant} className={className}>
        Choose {tier.name}
      </ButtonLink>
    )
  }
  return (
    <Button size="lg" variant={variant} className={className} disabled={access !== 'verified'} onClick={() => onChoose(tier)}>
      Choose {tier.name}
    </Button>
  )
}

/** Desktop tiers (design: "Join step 1 · desktop"): 320px cards, the featured one highlighted. */
function TierCards({ tiers, access, onChoose }: { tiers: Tier[]; access: Access; onChoose: (tier: Tier) => void }) {
  return (
    <ul className="hidden flex-wrap justify-center gap-6 pt-3 lg:flex">
      {tiers.map((tier) => (
        <TierCard
          key={tier.slug}
          tier={tier}
          tag={tier.is_featured ? { label: 'Most popular', tone: 'featured' } : undefined}
          action={<ChooseButton tier={tier} access={access} onChoose={onChoose} className="w-full" />}
          className="w-[320px]"
        />
      ))}
    </ul>
  )
}

/** Phone tiers (design: "Join step 1 · phone"): compact rows to pick from, then "Continue with …". */
function TierRows({ tiers, access, onChoose }: { tiers: Tier[]; access: Access; onChoose: (tier: Tier) => void }) {
  const [picked, setPicked] = useState((tiers.find((t) => t.is_featured) ?? tiers[0])?.slug)
  const tier = tiers.find((t) => t.slug === picked) ?? tiers[0]
  return (
    <div className="flex flex-col gap-4 lg:hidden">
      <fieldset className="flex flex-col gap-3">
        <legend className="sr-only">Tier</legend>
        {tiers.map((option) => {
          const selected = option.slug === tier?.slug
          return (
            <label
              key={option.slug}
              className={cn(
                'flex cursor-pointer items-center gap-4 rounded-card border-[1.5px] p-5 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-link',
                selected ? 'border-primary bg-tier-selected' : 'border-border bg-canvas',
              )}
            >
              <input type="radio" name="tier" value={option.slug} checked={selected} onChange={() => setPicked(option.slug)} className="sr-only" />
              <span className="flex flex-1 flex-col">
                <span className="font-display text-[1.375rem] leading-[1.3] text-fg">{option.name}</span>
                {option.description && <span className="text-[0.8125rem] text-fg-muted">{option.description}</span>}
              </span>
              <span className="flex flex-col items-end text-right">
                <span className="font-display text-[1.75rem] leading-none text-fg">{formatMoney(option.price_cents, option.currency)}</span>
                <span className="mt-1 text-xs text-fg-muted">{billingLabel(option)}</span>
              </span>
            </label>
          )
        })}
      </fieldset>
      {tier &&
        (access === 'anonymous' ? (
          <ButtonLink to={registerFor(tier)} size="lg" className="w-full">
            Continue with {tier.name}
          </ButtonLink>
        ) : (
          <Button size="lg" className="w-full" disabled={access !== 'verified'} onClick={() => onChoose(tier)}>
            Continue with {tier.name}
          </Button>
        ))}
    </div>
  )
}

/** The page title over the tiers, from the page's editable copy. */
function TierIntro({ copy }: { copy: PageCopy }) {
  return (
    <div className="flex flex-col gap-3 lg:items-center lg:gap-2 lg:text-center">
      <JoinProgress current={1} caption="Choose a tier" />
      <h1 className="text-[2rem] font-light leading-[1.05] text-fg lg:text-h1">
        {copy.status === 'loading' ? (
          <>
            <span className="sr-only">Join</span>
            <CopySkeleton className="w-[12ch]" />
          </>
        ) : (
          <Copy copy={copy} k="hero.title" as="span" />
        )}
      </h1>
      <Copy copy={copy} k="hero.lede" lines={1} className="text-sm text-fg-muted lg:text-lead" />
    </div>
  )
}

/** A quiet notice above the tiers (cancelled checkout, unverified email, signing in). */
function Notice({ children, role }: { children: ReactNode; role?: 'status' }) {
  return (
    <div role={role} className="mx-auto w-full max-w-[680px] rounded-card bg-blush p-5 text-sm text-fg-muted-tint lg:text-center">
      {children}
    </div>
  )
}

/** How to pay, the last part of step 2 (no design: laid out like the agreement, choices like the tier cards). */
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
      className="grid gap-6 lg:grid-cols-[420px_1fr] lg:gap-20"
    >
      <div className="flex flex-col gap-3 lg:gap-4">
        <JoinProgress current={2} caption="Payment" />
        <h1 id="method-heading" className="text-[2rem] font-light leading-[1.05] text-fg lg:text-h2-lg">
          How would you like to pay?
        </h1>
        <p className="text-fg-muted lg:text-base">Your bank statement shows a neutral name and the word &ldquo;Membership&rdquo;.</p>
        <div className="lg:mt-2">
          <TierSummary tier={tier} />
        </div>
      </div>
      <div className="flex flex-col gap-5">
        <fieldset className="flex flex-col gap-3">
          <legend className="sr-only">Payment method</legend>
          {methods.map((option) => {
            const selected = method === option.key
            return (
              <label
                key={option.key}
                className={cn(
                  'flex cursor-pointer items-start gap-4 rounded-card border-[1.5px] p-5 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-link sm:p-6',
                  selected ? 'border-primary bg-tier-selected' : 'border-border bg-canvas hover:border-fg-muted',
                )}
              >
                <input
                  type="radio"
                  name="method"
                  value={option.key}
                  checked={selected}
                  onChange={() => setMethod(option.key)}
                  className="mt-1 size-[18px] shrink-0 accent-[var(--color-primary)]"
                />
                <span>
                  <span className="block font-display text-[1.375rem] leading-[1.3] text-fg">{option.label}</span>
                  <span className="mt-1 block text-sm text-fg-muted">
                    {option.online
                      ? 'Pay now on a secure checkout page. Your membership starts once payment is confirmed and staff have seen your photo ID once.'
                      : 'Get a reference code now. Bring it, your payment and a valid photo ID on your first visit, and staff will start your membership at the door.'}
                  </span>
                </span>
              </label>
            )
          })}
        </fieldset>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <Button type="submit" size="lg" disabled={busy} aria-busy={busy}>
            {busy ? 'Working' : methods.find((m) => m.key === method)?.online ? 'Continue to checkout' : 'Get my reference code'}
          </Button>
          <button type="button" onClick={onBack} disabled={busy} className={BACK_BUTTON}>
            Back
          </button>
        </div>
      </div>
    </form>
  )
}

function ExistingMembership({ membership }: { membership: MyMembership }) {
  return (
    <div className="mx-auto flex max-w-[560px] flex-col items-center gap-3 rounded-panel bg-blush px-6 py-10 text-center">
      <h1 className="text-[2rem] font-light leading-[1.1] text-fg lg:text-h2-lg">You already have a membership</h1>
      <p className="text-fg-muted-tint">
        {membership.tier.name} &middot; {membership.status_label}. Your code, payments and renewal are on your account page.
      </p>
      <ButtonLink to="/account#membership" size="lg" className="mt-3">
        See my membership
      </ButtonLink>
    </div>
  )
}

function SignInFirst({ guest }: { guest?: Tier }) {
  const next = encodeURIComponent(guest ? `/join?tier=${guest.slug}` : '/join')
  return (
    <p className="text-sm text-fg-muted lg:text-center">
      {guest
        ? 'A guest pass takes a free account, so your code and ID check are there for your next visit too. '
        : 'Joining takes a free account, so your membership has somewhere private to live. '}
      <Link to={`/account/register?next=${next}`} className="font-semibold text-link hover:text-primary-hover">
        Create an account
      </Link>{' '}
      or{' '}
      <Link to={`/account/login?next=${next}`} className="font-semibold text-link hover:text-primary-hover">
        log in
      </Link>
      .
    </p>
  )
}

function Benefits({ copy }: { copy: PageCopy }) {
  const items = copy.status === 'loading' ? [1, 2, 3, 4] : copy.items('benefits')
  if (items.length === 0) return null
  return (
    <section aria-labelledby="benefits" className="mt-14 border-t border-border pt-10 lg:mt-20 lg:pt-16">
      <CopyHeading copy={copy} prefix="benefits" id="benefits" />
      <ul className="mt-8 grid gap-x-6 gap-y-8 sm:grid-cols-2 lg:mt-10 lg:grid-cols-4">
        {items.map((n) => (
          <li key={n} className="flex flex-col gap-2">
            <Copy copy={copy} k={`benefits.${n}.title`} as="h3" className="text-xl text-fg lg:text-card-title" />
            <Copy copy={copy} k={`benefits.${n}.body`} lines={2} className="text-sm text-fg-muted" />
          </li>
        ))}
      </ul>
    </section>
  )
}

function JoinFlow({
  tiers,
  options,
  existing,
  reloadOptions,
  preselected,
  copy,
  cancelled,
}: {
  tiers: Tier[]
  options: JoinOptions
  existing: MyMembership | null
  reloadOptions: () => void
  preselected: Tier | null
  copy: PageCopy
  cancelled: boolean
}) {
  const auth = useAuth()
  const toast = useToast()
  const guest = preselected?.is_guest_pass ? preselected : null
  const verified = Boolean(auth.user?.email_verified)
  const access: Access = !auth.user ? 'anonymous' : verified ? 'verified' : 'unverified'
  // A tier chosen before signing in, or a guest arriving from the Guests page, goes straight to the agreement.
  const [step, setStep] = useState<Step>(preselected && verified ? { name: 'agreement', tier: preselected } : { name: 'tiers' })
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
        <JoinSteps current={3} />
        <div className={JOIN_FRAME}>
          <JoinConfirmation membership={step.membership} />
        </div>
      </div>
    )
  }
  // A guest becoming a member gives up their open guest pass; anything else stops here.
  const guestPassOpen = isOpen(existing) && existing.tier.is_guest_pass
  if (isOpen(existing) && (!guestPassOpen || guest)) {
    return (
      <div className={JOIN_FRAME}>
        <ExistingMembership membership={existing} />
      </div>
    )
  }
  const offered = membershipTiers(tiers)
  // Chosen on the membership page while signed out: an account comes first.
  if (preselected && !guest && access === 'anonymous') return <Navigate to={registerFor(preselected)} replace />
  if (!agreement || (!guest && offered.length === 0)) {
    return (
      <div className={JOIN_FRAME}>
        <TierIntro copy={copy} />
        <div className="mx-auto mt-8 max-w-[680px]">
          <EmptyState
            title="Joining online is not open yet"
            message="Start with a newcomer orientation on any Thursday and our hosts will walk you through membership in person."
          />
        </div>
      </div>
    )
  }

  /** A free tier has nothing to pay, so it has no method. */
  async function join(tier: Tier, typedName: string, method?: string) {
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

  // Guest passes are paid at the door, never online.
  const methodsFor = (tier: Tier) => (tier.is_guest_pass ? options.methods.filter((m) => !m.online) : options.methods)
  const choose = (tier: Tier) => setStep({ name: 'agreement', tier })
  const shown = guest ? [guest] : offered

  return (
    <div ref={top} className="scroll-mt-24">
      <JoinSteps current={step.name === 'tiers' ? 1 : 2} />
      <div className={JOIN_FRAME}>
        {step.name === 'tiers' && (
          <>
            <TierIntro copy={copy} />
            <div className="mt-6 flex flex-col gap-3 empty:hidden lg:mt-8">
              {cancelled && (
                <Notice role="status">Checkout was cancelled and nothing was charged. You can pick up where you left off below.</Notice>
              )}
              {guestPassOpen && <Notice role="status">Choosing a membership replaces your guest pass. Your ID check carries over.</Notice>}
              {access === 'unverified' && auth.user && (
                <Notice role="status">Confirm your email first. Open the link we sent to {auth.user.email}, then come back here.</Notice>
              )}
            </div>
            <div className="mt-6 lg:mt-8">
              <TierCards tiers={shown} access={access} onChoose={choose} />
              <TierRows tiers={shown} access={access} onChoose={choose} />
            </div>
            <div className="mt-6 flex flex-col gap-2 lg:mt-8">
              {access === 'anonymous' && <SignInFirst guest={guest ?? undefined} />}
              <Copy copy={copy} k="note" className="text-sm text-fg-muted lg:text-center" />
            </div>
            <Benefits copy={copy} />
          </>
        )}
        {step.name === 'agreement' && (
          <AgreementStep
            key={agreement.version}
            agreement={agreement}
            tier={step.tier}
            notice={step.notice}
            onBack={() => setStep({ name: 'tiers' })}
            busy={busy}
            submitLabel={step.tier.is_free ? 'Agree and get my code' : undefined}
            onSigned={(typedName) =>
              step.tier.is_free ? void join(step.tier, typedName) : setStep({ name: 'method', tier: step.tier, typedName })
            }
          />
        )}
        {step.name === 'method' && (
          <MethodStep
            tier={step.tier}
            methods={methodsFor(step.tier)}
            busy={busy}
            onBack={() => setStep({ name: 'agreement', tier: step.tier })}
            onSubmit={(method) => void join(step.tier, step.typedName, method)}
          />
        )}
      </div>
    </div>
  )
}

/**
 * Join (design: "Join step 1–3"): tier, agreement (with the payment method), confirmation.
 * The steps sit in a band under the site header rather than replacing it.
 */
export function JoinPage() {
  useDocumentMeta({ title: 'Join', description: 'What membership includes and how to become a member.' })
  const auth = useAuth()
  const [params] = useSearchParams()
  const cancelled = params.get('cancelled') === '1'
  const wanted = params.get('tier')
  const copy = usePageContent('join')
  const tiers = useAsync(() => membershipApi.tiers(), 'tiers')
  const options = useAsync(() => membershipApi.options(), 'join-options')
  const signedIn = auth.user ? auth.user.display_name : ''
  const me = useAsync(() => (signedIn ? membershipApi.me() : Promise.resolve(null)), `me:${signedIn}`)

  if (tiers.status === 'loading' || options.status === 'loading' || (signedIn && me.status === 'loading') || auth.status === 'loading') {
    return (
      <>
        <JoinSteps current={1} />
        <div className={JOIN_FRAME}>
          <TierIntro copy={copy} />
          <LoadingState label="Loading membership options" className="justify-center" />
        </div>
      </>
    )
  }
  if (tiers.status === 'error' || options.status === 'error' || me.status === 'error') {
    return (
      <>
        <JoinSteps current={1} />
        <div className={JOIN_FRAME}>
          <TierIntro copy={copy} />
          <ErrorState
            className="mx-auto mt-8 max-w-[680px]"
            title="Membership options did not load"
            onRetry={() => {
              tiers.retry()
              options.retry()
              me.retry()
            }}
          />
        </div>
      </>
    )
  }
  return (
    <JoinFlow
      key={signedIn}
      tiers={tiers.data}
      options={options.data}
      existing={me.data?.membership ?? null}
      reloadOptions={options.retry}
      preselected={tiers.data.find((tier) => tier.slug === wanted) ?? null}
      copy={copy}
      cancelled={cancelled}
    />
  )
}

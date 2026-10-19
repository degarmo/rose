import { Check, Info, Minus } from 'lucide-react'
import type { ReactNode } from 'react'
import { Copy, CopyHeading } from '@/components/content/Copy'
import { PageHero } from '@/components/content/PageHero'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { SubscribeForm } from '@/components/layout/SubscribeForm'
import { TierCard } from '@/components/membership/TierCard'
import { ButtonLink, GUTTER, Section } from '@/components/ui'
import { cn } from '@/lib/cn'
import { formatDay, formatMoney } from '@/lib/format'
import { billingLabel, eventsLeftLabel, membershipApi, membershipTiers, type MyMembership, type Tier } from '@/lib/membershipApi'
import { usePageContent, type PageCopy } from '@/lib/pageContent'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

const BAND = cn('mx-auto max-w-[1440px]', GUTTER)

/** The membership that is running now, if the signed-in person has one. */
function useCurrentMembership(): MyMembership | null {
  const auth = useAuth()
  const signedIn = auth.user ? auth.user.display_name : ''
  const me = useAsync(() => (signedIn ? membershipApi.me() : Promise.resolve(null)), `me:${signedIn}`)
  const membership = me.status === 'success' ? (me.data?.membership ?? null) : null
  return membership && (membership.status === 'active' || membership.status === 'grace') ? membership : null
}

function periodText(membership: MyMembership) {
  const end = membership.current_period_end
  if (!end) return null
  if (membership.status === 'grace') return `Renewal was due ${formatDay(end)}`
  if (membership.tier.renews && !membership.cancel_at_period_end) return `Renews ${formatDay(end)}`
  return `Ends ${formatDay(end)}`
}

/** For members: their tier, when it renews or ends, and the events left this month. */
function MemberBanner({ membership }: { membership: MyMembership }) {
  const facts = [periodText(membership), eventsLeftLabel(membership)].filter(Boolean)
  return (
    <section aria-label="Your membership" className={cn(BAND, 'pb-2')}>
      <div className="flex flex-col gap-3 rounded-card bg-blush p-5 sm:flex-row sm:items-center sm:justify-between lg:px-8">
        <div className="flex flex-col gap-1">
          <p className="font-display text-[1.375rem] leading-[1.2] text-fg">Your plan: {membership.tier.name}</p>
          <p className="text-sm text-fg-muted-tint">{facts.join(' · ')}</p>
        </div>
        <ButtonLink to="/account#membership" variant="secondary" className="self-start sm:self-auto">
          Manage
        </ButtonLink>
      </div>
    </section>
  )
}

/** Every tier, lowest price first (the API's order), four to a row on wide screens. */
function Plans({ tiers, current }: { tiers: Tier[]; current: MyMembership | null }) {
  return (
    <section aria-label="Plans" className={cn(BAND, 'pb-12 pt-6 lg:pb-20 lg:pt-8')}>
      <ul className="grid gap-x-6 gap-y-9 pt-3 md:grid-cols-2 wide:grid-cols-4">
        {tiers.map((tier) => {
          const mine = current?.tier.slug === tier.slug
          const tag = mine ? { label: 'Your plan', tone: 'current' as const } : tier.is_featured ? { label: 'Most popular', tone: 'featured' as const } : undefined
          return (
            <TierCard
              key={tier.slug}
              tier={tier}
              tag={tag}
              action={
                mine ? (
                  <ButtonLink to="/account#membership" size="lg" variant="secondary" className="w-full">
                    Manage
                  </ButtonLink>
                ) : (
                  <ButtonLink
                    to={`/join?tier=${encodeURIComponent(tier.slug)}`}
                    size="lg"
                    variant={tier.is_featured ? 'primary' : 'outline'}
                    className="w-full"
                    aria-label={`Choose ${tier.name}`}
                  >
                    Choose
                  </ButtonLink>
                )
              }
            />
          )
        })}
      </ul>
    </section>
  )
}

function YesNo({ value }: { value: boolean }) {
  return value ? (
    <>
      <Check aria-hidden="true" className="size-4 text-link" />
      <span className="sr-only">Yes</span>
    </>
  ) : (
    <>
      <Minus aria-hidden="true" className="size-4 text-fg-muted" />
      <span className="sr-only">No</span>
    </>
  )
}

function priceText(tier: Tier) {
  if (tier.is_free) return billingLabel(tier).replace(/^free/, 'Free')
  return `${formatMoney(tier.price_cents, tier.currency)} ${billingLabel(tier)}`
}

function renewsText(tier: Tier) {
  if (!tier.renews) return 'No'
  if (tier.is_free) return 'Ongoing'
  return tier.interval === 'year' ? 'Yearly' : 'Monthly'
}

function eventsText(tier: Tier) {
  if (tier.event_access === 'all') return 'All club events'
  return `${tier.allowed_event_tags.map((tag) => tag.name).join(', ')} events`
}

/** The comparison rows, in the order the page shows them. */
const ROWS: Array<{ label: string; cell: (tier: Tier) => ReactNode }> = [
  { label: 'Price', cell: priceText },
  { label: 'Renews', cell: renewsText },
  { label: 'Events per month', cell: (tier) => (tier.events_per_month === null ? 'Unlimited' : String(tier.events_per_month)) },
  { label: 'Guests included', cell: (tier) => (tier.guests_included_per_event === 0 ? 'None' : `${tier.guests_included_per_event} per event`) },
  { label: 'Guest discount', cell: (tier) => <YesNo value={tier.guest_discount} /> },
  { label: 'Premium Discord', cell: (tier) => <YesNo value={tier.premium_discord} /> },
  { label: 'Member community', cell: (tier) => <YesNo value={tier.grants_feed_access} /> },
  { label: 'Which events', cell: eventsText },
]

/** Compare plans: a table on large screens, one short list per tier below that. */
function Compare({ tiers, copy }: { tiers: Tier[]; copy: PageCopy }) {
  return (
    <Section rule aria-labelledby="compare">
      <CopyHeading copy={copy} prefix="compare" id="compare" />
      <table className="hidden w-full table-fixed border-collapse text-sm lg:table">
        <thead>
          <tr className="border-b border-border">
            <td className="w-[15%]" />
            {tiers.map((tier) => (
              <th key={tier.slug} scope="col" className="px-2 pb-3 text-left font-display text-lg font-normal text-fg">
                {tier.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => (
            <tr key={row.label} className="border-b border-border">
              <th scope="row" className="py-3 pr-2 text-left font-semibold text-fg">
                {row.label}
              </th>
              {tiers.map((tier) => (
                <td key={tier.slug} className="px-2 py-3 align-top text-fg-muted">
                  {row.cell(tier)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="grid gap-x-8 gap-y-6 sm:grid-cols-2 lg:hidden">
        {tiers.map((tier) => (
          <li key={tier.slug} className="border-t border-border pt-4">
            <h3 className="font-display text-xl text-fg">{tier.name}</h3>
            <dl className="mt-2 flex flex-col text-sm">
              {ROWS.map((row) => (
                <div key={row.label} className="flex justify-between gap-4 border-b border-border py-2 last:border-b-0">
                  <dt className="text-fg">{row.label}</dt>
                  <dd className="flex items-center text-right text-fg-muted">{row.cell(tier)}</dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
    </Section>
  )
}

/** Good to know: cancelling, refunds, ID, guests (staff-editable), and the email tip. */
function GoodToKnow({ copy }: { copy: PageCopy }) {
  const items = copy.status === 'loading' ? [1, 2, 3] : copy.items('good_to_know')
  return (
    <Section rule aria-labelledby="good-to-know">
      <div className="grid gap-6 lg:grid-cols-[1fr_400px] lg:gap-16">
        <div>
          <CopyHeading copy={copy} prefix="good_to_know" id="good-to-know" />
          <ul className="flex flex-col">
            {items.map((n) => (
              <li key={n} className="flex gap-3 border-t border-border py-3 text-fg-muted lg:py-4 lg:text-[1.0625rem]">
                <Check aria-hidden="true" className="mt-1 size-4 shrink-0 text-link" />
                <Copy copy={copy} k={`good_to_know.${n}`} as="div" className="[&_p]:m-0" />
              </li>
            ))}
          </ul>
        </div>
        {(copy.status === 'loading' || copy.text('tip')) && (
          <aside aria-label="Tip" className="flex gap-3 self-start rounded-card bg-surface p-5 text-sm text-fg-muted lg:mt-16">
            <Info aria-hidden="true" className="mt-0.5 size-[18px] shrink-0 text-fg-muted" strokeWidth={1.8} />
            <Copy copy={copy} k="tip" className="flex-1" />
          </aside>
        )}
      </div>
    </Section>
  )
}

function Closing({ copy }: { copy: PageCopy }) {
  return (
    <Section rule spacing="none" aria-labelledby="closing" className="py-14 lg:py-24">
      <div className="flex flex-col items-center gap-4 text-center lg:gap-6">
        <Copy copy={copy} k="cta.title" as="h2" id="closing" lines={2} className="w-full max-w-[640px] text-[2.125rem] font-light leading-[1.1] text-fg lg:text-h2-lg" />
        <Copy copy={copy} k="cta.body" className="max-w-[560px] text-fg-muted lg:text-lead" />
        <ButtonLink to="/visit" size="lg">
          {copy.text('cta.button') || 'Plan your visit'}
        </ButtonLink>
        {copy.text('newsletter') && (
          <div className="mt-6 w-full max-w-[420px] text-left text-sm lg:mt-8">
            <SubscribeForm label={copy.text('newsletter')} />
          </div>
        )}
      </div>
    </Section>
  )
}

/**
 * Membership (no design of its own; the cards are Join step 1's). Every price, perk and
 * rule comes from the tiers the API offers, lowest price first.
 */
export function MembershipPage() {
  useDocumentMeta({ title: 'Membership', description: 'Membership plans, what each includes, and how to join.' })
  const copy = usePageContent('membership')
  const tiers = useAsync(() => membershipApi.tiers(), 'tiers')
  const current = useCurrentMembership()

  let plans: ReactNode
  if (tiers.status === 'loading') plans = <LoadingState label="Loading membership plans" className={cn(BAND, 'py-10')} />
  else if (tiers.status === 'error')
    plans = <ErrorState className={cn(BAND, 'my-10 max-w-[680px]')} title="Membership plans did not load" onRetry={tiers.retry} />
  else {
    const offered = membershipTiers(tiers.data)
    plans =
      offered.length === 0 ? (
        <div className={cn(BAND, 'pb-12 pt-6 lg:pb-20 [&>*]:max-w-[680px]')}>
          <EmptyState
            title="Membership plans are not online yet"
            message="Come to a newcomer orientation on any Thursday and our hosts will walk you through membership in person."
          />
        </div>
      ) : (
        <>
          <Plans tiers={offered} current={current} />
          <Compare tiers={offered} copy={copy} />
        </>
      )
  }

  return (
    <>
      <PageHero copy={copy} />
      {current && <MemberBanner membership={current} />}
      {plans}
      <GoodToKnow copy={copy} />
      <Closing copy={copy} />
    </>
  )
}

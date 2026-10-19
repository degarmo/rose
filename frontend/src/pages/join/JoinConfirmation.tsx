import { Banknote, IdCard, QrCode } from 'lucide-react'
import { useAuth } from '@/components/layout/authContext'
import { ReferenceCode } from '@/components/membership/ReferenceCode'
import { ButtonLink } from '@/components/ui'
import { formatDay } from '@/lib/format'
import { priceLabel, type MyMembership } from '@/lib/membershipApi'
import { JoinProgress } from './JoinSteps'

/** What to bring on a first visit. Used after joining and on the account card. */
export function WhatToBring({ membership }: { membership: MyMembership }) {
  const items = [
    { icon: QrCode, text: 'This code, on your phone or written down.' },
    ...(membership.paid_awaiting_id_check
      ? []
      : [{ icon: Banknote, text: `Your payment: ${priceLabel(membership.tier)}, by cash or card.` }]),
    { icon: IdCard, text: 'A valid photo ID showing you are 18 or older. Staff only check it; nothing is copied or kept.' },
  ]
  return (
    <ul className="flex flex-col gap-2.5 text-sm">
      {items.map(({ icon: Icon, text }) => (
        <li key={text} className="flex gap-3 text-fg-muted">
          <Icon aria-hidden="true" className="mt-0.5 size-[18px] shrink-0 text-link" strokeWidth={1.8} />
          {text}
        </li>
      ))}
    </ul>
  )
}

/** The lines under the door reference's QR: the tier and how long the code is good for. */
export function CodeValidity({ membership }: { membership: MyMembership }) {
  const { tier, status, code_expires_at, current_period_end } = membership
  let until: string | null = null
  if (status === 'pending_payment' && code_expires_at) until = `code open until ${formatDay(code_expires_at)}`
  else if ((status === 'active' || status === 'grace') && current_period_end) until = `valid through ${formatDay(current_period_end)}`
  return (
    <>
      {tier.name}
      {until && (
        <>
          {' '}
          &middot; <span className="whitespace-nowrap">{until}</span>
        </>
      )}
      <br />
      It identifies your membership, not you.
    </>
  )
}

/** The way on from a confirmation: the member app once it is open to them, otherwise the account. */
export function ConfirmationActions({ secondary }: { secondary?: { to: string; label: string } }) {
  const auth = useAuth()
  const app = Boolean(auth.user?.feed_access)
  const next = app ? { to: '/account#membership', label: 'Go to my account' } : (secondary ?? { to: '/visit', label: 'Plan your visit' })
  return (
    <div className="flex flex-col gap-2.5 sm:flex-row sm:gap-3">
      {app ? (
        <ButtonLink to="/members/feed" size="lg">
          Open the member app
        </ButtonLink>
      ) : (
        <ButtonLink to="/account#membership" size="lg">
          Go to my account
        </ButtonLink>
      )}
      <ButtonLink to={next.to} size="lg" variant="secondary">
        {next.label}
      </ButtonLink>
    </div>
  )
}

/** "Welcome, night_owl.": the person's display name, never the name they signed with. */
export function WelcomeHeading({ id }: { id?: string }) {
  const auth = useAuth()
  const name = auth.user?.display_name
  return (
    <h1 id={id} className="text-[2rem] font-light leading-[1.05] text-fg lg:text-h1">
      {name ? `Welcome, ${name}.` : 'Welcome.'}
    </h1>
  )
}

interface DoorWelcomeProps {
  membership: MyMembership
  label: string
  lead: string
  secondary?: { to: string; label: string }
  bring: boolean
}

/**
 * Join step 3 (design: "Join step 3"): "You're in", the welcome and what happens at the
 * door on the left; the blush door reference with its QR on the right.
 */
export function DoorWelcome({ membership, label, lead, secondary, bring }: DoorWelcomeProps) {
  return (
    <article
      aria-labelledby="confirmation-heading"
      className="flex flex-col gap-5 lg:grid lg:grid-cols-[minmax(0,460px)_400px] lg:justify-center lg:gap-x-24 lg:gap-y-5 lg:py-12"
    >
      <div className="flex flex-col gap-3 lg:col-start-1 lg:row-start-1 lg:gap-5 lg:self-end">
        <JoinProgress current={3} />
        <p className="text-xs font-semibold uppercase tracking-[0.06em] text-link">{label}</p>
        <WelcomeHeading id="confirmation-heading" />
        <p className="text-sm text-fg-muted lg:text-lead">{lead}</p>
      </div>
      <ReferenceCode code={membership.reference_code} className="lg:col-start-2 lg:row-span-3 lg:row-start-1 lg:self-center">
        <CodeValidity membership={membership} />
      </ReferenceCode>
      <div className="lg:col-start-1 lg:row-start-2">
        <ConfirmationActions secondary={secondary} />
      </div>
      {bring && (
        <section aria-labelledby="bring-heading" className="flex flex-col gap-3 lg:col-start-1 lg:row-start-3 lg:self-start">
          <h2 id="bring-heading" className="font-sans text-sm font-semibold text-fg">
            What to bring
          </h2>
          <WhatToBring membership={membership} />
        </section>
      )}
    </article>
  )
}

/** Right after joining with a pay-at-the-door method. */
export function JoinConfirmation({ membership }: { membership: MyMembership }) {
  const { tier } = membership
  const guest = tier.is_guest_pass
  // A free tier starts at once when an ID check from an earlier visit is on file.
  const started = membership.status === 'active'
  let lead: string
  if (started) lead = `Your ${tier.name} membership has started. Show this code at the door when you visit.`
  else if (guest)
    lead =
      'Show this code and your photo ID at the door on the night you visit. Staff check your ID, take payment and you are in for the evening. The same account and code work next time too.'
  else if (tier.is_free)
    lead = `Show this code and your photo ID at the door on your first visit. Staff check your ID and start your ${tier.name} membership there. There is nothing to pay.`
  else lead = `Show this code and your photo ID at the door on your first visit, and staff will start your ${tier.name} membership there.`
  return (
    <DoorWelcome
      membership={membership}
      label={guest ? 'Your guest pass is ready' : "You're in"}
      lead={started ? lead : `${lead} We have emailed you this code too.`}
      bring={!started}
    />
  )
}

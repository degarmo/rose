import { BadgeCheck, Banknote, IdCard, QrCode } from 'lucide-react'
import { ReferenceCode } from '@/components/membership/ReferenceCode'
import { ButtonLink, Card } from '@/components/ui'
import { formatDay } from '@/lib/format'
import { priceLabel, type MyMembership } from '@/lib/membershipApi'

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
    <ul className="flex flex-col gap-3">
      {items.map(({ icon: Icon, text }) => (
        <li key={text} className="flex gap-3 text-fg-muted">
          <Icon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-highlight" />
          {text}
        </li>
      ))}
    </ul>
  )
}

export function JoinConfirmation({ membership }: { membership: MyMembership }) {
  const guest = membership.tier.is_guest_pass
  return (
    <Card as="article" aria-labelledby="confirmation-heading" className="p-6 sm:p-8">
      <h2 id="confirmation-heading" className="flex items-center gap-3 text-3xl text-fg">
        <BadgeCheck aria-hidden="true" className="size-7 text-success" />
        {guest ? 'Your guest pass is ready' : 'You are almost a member'}
      </h2>
      <p className="mt-3 text-fg-muted">
        {guest
          ? 'Show this code at the door on the night you visit. Staff check your ID, take payment and you are in for the evening. Next time, the same account and code work again.'
          : `Staff will start your ${membership.tier.name.toLowerCase()} membership at the door on your first visit.`}{' '}
        We have emailed you this code too.
      </p>
      <ReferenceCode code={membership.reference_code} className="mt-8" />
      <h3 className="mt-10 text-xl text-fg">What to bring</h3>
      <div className="mt-4">
        <WhatToBring membership={membership} />
      </div>
      {membership.code_expires_at && (
        <p className="mt-6 text-sm text-fg-subtle">
          This code stays open until {formatDay(membership.code_expires_at)}. After that, simply join again.
        </p>
      )}
      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <ButtonLink to="/account#membership" size="lg">
          Go to my account
        </ButtonLink>
        <ButtonLink to="/visit" size="lg" variant="ghost">
          Plan your visit
        </ButtonLink>
      </div>
    </Card>
  )
}

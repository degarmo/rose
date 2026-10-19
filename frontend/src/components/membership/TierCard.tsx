import { Check } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'
import { formatMoney } from '@/lib/format'
import { billingLabel, type Tier } from '@/lib/membershipApi'

interface TierCardProps {
  tier: Tier
  /** The pill on the top edge: "Most popular" on the featured tier, "Your plan" on yours. */
  tag?: { label: string; tone: 'featured' | 'current' }
  /** The card's button, at the bottom. */
  action: ReactNode
  as?: 'li' | 'div'
  className?: string
}

/**
 * A membership tier (design: "Join step 1 · desktop"): 20px corners, the name in Fraunces
 * 26, the price in Fraunces 44 with its billing label, a one-line summary, the perks with
 * ticks and the button. The featured tier has the 1.5px rose border and a tinted card.
 * Used by Join step 1 and the membership page.
 */
export function TierCard({ tier, tag, action, as: Element = 'li', className }: TierCardProps) {
  const featured = tier.is_featured
  return (
    <Element
      className={cn(
        'relative flex flex-col gap-3 rounded-panel border-[1.5px] p-8',
        featured ? 'border-primary bg-tier-selected' : 'border-border bg-canvas',
        className,
      )}
    >
      {tag && (
        <span
          className={cn(
            'absolute -top-3 left-8 rounded-full px-2.5 py-1 text-label font-semibold uppercase tracking-[0.06em]',
            tag.tone === 'featured' ? 'bg-primary text-on-primary' : 'bg-fg text-canvas',
          )}
        >
          {tag.label}
        </span>
      )}
      <h2 className="text-[1.625rem] leading-[1.2] text-fg">{tier.name}</h2>
      <p className="flex flex-wrap items-baseline gap-x-1">
        <span className="font-display text-[2.75rem] leading-none text-fg">{formatMoney(tier.price_cents, tier.currency)}</span>
        <span className="text-fg-muted">{billingLabel(tier)}</span>
      </p>
      <div className="flex flex-1 flex-col gap-3 text-sm text-fg-muted">
        {tier.description && <p>{tier.description}</p>}
        {tier.perks.length > 0 && (
          <ul className="flex flex-col gap-1.5">
            {tier.perks.map((perk) => (
              <li key={perk} className="flex gap-2">
                <Check aria-hidden="true" className="mt-[3px] size-4 shrink-0 text-link" />
                {perk}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="mt-3">{action}</div>
    </Element>
  )
}

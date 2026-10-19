import { Lock } from 'lucide-react'
import { useLocation } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { ButtonLink } from '@/components/ui'
import { cn } from '@/lib/cn'

interface PaywallPanelProps {
  title: string
  /** One sentence on what membership adds here, e.g. "The full description is in the member area." */
  benefit: string
  /** Tier names that unlock this, when the server lists them. */
  tiers?: string[]
  /** `sm` sits inside a card (13px text, 36px buttons); `lg` stands on a page. */
  size?: 'sm' | 'lg'
  headingLevel?: 'h2' | 'h3' | 'h4'
  className?: string
}

function tierSentence(tiers: string[]) {
  if (tiers.length === 0) return null
  if (tiers.length === 1) return `Included with ${tiers[0]} membership.`
  return `Included with ${tiers.slice(0, -1).join(', ')} and ${tiers[tiers.length - 1]} memberships.`
}

/**
 * The one way the site says "this comes with membership" (design system: "Paywall"): a
 * blush panel with an oxblood lock. Visitors get Join and Log in; signed-in people without
 * a membership get Join; people with one get a link to their account.
 */
export function PaywallPanel({ title, benefit, tiers = [], size = 'sm', headingLevel = 'h3', className }: PaywallPanelProps) {
  const auth = useAuth()
  const { pathname, search } = useLocation()
  const next = encodeURIComponent(`${pathname}${search}`)
  const Heading = headingLevel
  const includes = tierSentence(tiers)
  const buttonSize = size === 'lg' ? 'md' : 'sm'

  let actions
  if (auth.status === 'loading') {
    actions = <p className="text-fg-muted-tint">Checking your account</p>
  } else if (auth.user?.has_membership) {
    actions = (
      <ButtonLink to="/account#membership" size={buttonSize} variant="secondary">
        See my membership
      </ButtonLink>
    )
  } else {
    actions = (
      <>
        <ButtonLink to="/join" size={buttonSize}>
          Join
        </ButtonLink>
        {!auth.user && (
          <ButtonLink to={`/account/login?next=${next}`} size={buttonSize} variant="secondary">
            Log in
          </ButtonLink>
        )}
      </>
    )
  }

  return (
    <div
      data-testid="paywall"
      className={cn('flex flex-col items-start rounded-field bg-blush', size === 'lg' ? 'gap-2 p-6 sm:p-8' : 'gap-1.5 p-4 sm:gap-2 sm:p-5', className)}
    >
      <Lock aria-hidden="true" strokeWidth={1.6} className="size-[22px] text-wordmark" />
      <Heading className={cn('text-fg', size === 'lg' ? 'text-2xl' : 'font-sans text-sm font-semibold')}>{title}</Heading>
      <p className={cn('text-fg-muted-tint', size === 'sm' && 'text-[0.8125rem]')}>{benefit}</p>
      {includes && <p className="text-[0.8125rem] text-fg-muted-tint">{includes}</p>}
      {auth.user?.has_membership && (
        <p className="text-[0.8125rem] text-fg-muted-tint">Your current membership does not include this, or is not active right now.</p>
      )}
      <div className="mt-1 flex flex-wrap gap-2">{actions}</div>
    </div>
  )
}

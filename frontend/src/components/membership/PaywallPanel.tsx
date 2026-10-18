import { KeyRound, UserPlus } from 'lucide-react'
import { useLocation } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { ButtonLink, Card } from '@/components/ui'
import { cn } from '@/lib/cn'

interface PaywallPanelProps {
  title: string
  /** One sentence on what membership adds here, e.g. "Members-only classes come with membership." */
  benefit: string
  /** Tier names that unlock this, when the server lists them. */
  tiers?: string[]
  /** "card" stands alone; "inline" sits inside another card. */
  variant?: 'card' | 'inline'
  headingLevel?: 'h2' | 'h3'
  className?: string
}

function tierSentence(tiers: string[]) {
  if (tiers.length === 0) return null
  if (tiers.length === 1) return `Included with ${tiers[0]} membership.`
  return `Included with ${tiers.slice(0, -1).join(', ')} and ${tiers[tiers.length - 1]} memberships.`
}

/**
 * The one way the site says "this comes with membership". Anonymous visitors
 * get log in and create account; signed-in people without a membership get
 * "Become a member"; people with a membership get a link to their account.
 */
export function PaywallPanel({ title, benefit, tiers = [], variant = 'card', headingLevel = 'h2', className }: PaywallPanelProps) {
  const auth = useAuth()
  const { pathname, search } = useLocation()
  const next = encodeURIComponent(`${pathname}${search}`)
  const Heading = headingLevel
  const includes = tierSentence(tiers)

  let actions
  if (auth.status === 'loading') {
    actions = <p className="text-sm text-fg-muted">Checking your account</p>
  } else if (!auth.user) {
    actions = (
      <>
        <ButtonLink to={`/account/login?next=${next}`} size="lg">
          Log in
        </ButtonLink>
        <ButtonLink to={`/account/register?next=${encodeURIComponent('/join')}`} size="lg" variant="ghost">
          <UserPlus aria-hidden="true" className="size-4" />
          Create an account
        </ButtonLink>
      </>
    )
  } else if (auth.user.has_membership) {
    actions = (
      <ButtonLink to="/account#membership" size="lg" variant="ghost">
        See my membership
      </ButtonLink>
    )
  } else {
    actions = (
      <ButtonLink to="/join" size="lg">
        Become a member
      </ButtonLink>
    )
  }

  const content = (
    <>
      <Heading className="flex items-center gap-3 font-display text-2xl text-fg">
        <KeyRound aria-hidden="true" className="size-5 shrink-0 text-highlight" />
        {title}
      </Heading>
      <p className="mt-2 text-fg-muted">{benefit}</p>
      {includes && <p className="mt-1 text-sm text-fg-subtle">{includes}</p>}
      {auth.user?.has_membership && (
        <p className="mt-1 text-sm text-fg-subtle">Your current membership does not include this, or is not active right now.</p>
      )}
      <div className="mt-6 flex flex-col gap-3 sm:flex-row">{actions}</div>
    </>
  )

  if (variant === 'inline') {
    return (
      <div data-testid="paywall" className={cn('flex flex-col', className)}>
        {content}
      </div>
    )
  }
  return (
    <Card as="article" data-testid="paywall" className={cn('p-6 sm:p-8', className)}>
      {content}
    </Card>
  )
}

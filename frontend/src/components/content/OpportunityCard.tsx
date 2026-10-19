import { Link } from 'react-router'
import { PaywallPanel } from '@/components/membership/PaywallPanel'
import type { Opportunity } from '@/lib/api'
import { formatShortDate } from '@/lib/format'
import { ButtonLink, Chip, ImageFrame } from '../ui'

/**
 * A class or workshop (design: "Education card"): a 3:2 picture (2:1 on phones) with the
 * level on it, then the date, the title, the summary and an outline button. A locked
 * members-only class shows the blush paywall instead of its summary.
 */
export function OpportunityCard({ opportunity, headingLevel = 'h3' }: { opportunity: Opportunity; headingLevel?: 'h2' | 'h3' }) {
  const Heading = headingLevel
  const detailPath = `/education/${opportunity.slug}`
  const cta = opportunity.cta_label && opportunity.cta_url ? { label: opportunity.cta_label, to: opportunity.cta_url } : { label: 'Details', to: detailPath }
  return (
    <article className="relative flex h-full flex-col overflow-hidden rounded-card border border-border bg-canvas">
      <div className="relative">
        <ImageFrame
          remote={opportunity.hero_image}
          alt=""
          ratio="3/2"
          placeholder="warm"
          className="aspect-[2/1] lg:aspect-[3/2]"
          sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
        />
        <Chip variant="solid" className="absolute left-3 top-3">
          {opportunity.level_label}
        </Chip>
      </div>
      <div className="flex flex-1 flex-col gap-1.5 px-5 pb-5 pt-4 lg:gap-2 lg:px-6 lg:pb-6 lg:pt-5">
        {opportunity.starts_at && (
          <p className="text-[0.8125rem] text-fg-muted">
            <time dateTime={opportunity.starts_at}>{formatShortDate(opportunity.starts_at)}</time>
          </p>
        )}
        <Heading className="text-xl leading-[1.2] text-fg lg:text-card-title">
          <Link to={detailPath} className="hover:text-link">
            {opportunity.title}
          </Link>
        </Heading>
        {opportunity.locked ? (
          <PaywallPanel
            className="mt-2 flex-1"
            title="For members"
            benefit={opportunity.paywall?.benefit || 'The full description, readings and sign-up are in the member area.'}
            tiers={opportunity.paywall?.tiers}
            headingLevel={headingLevel === 'h2' ? 'h3' : 'h4'}
          />
        ) : (
          <>
            <p className="flex-1 text-sm text-fg-muted">{opportunity.summary}</p>
            <ButtonLink to={cta.to} variant="outline" className="mt-2 self-start" aria-label={`${cta.label}: ${opportunity.title}`}>
              {cta.label}
            </ButtonLink>
          </>
        )}
      </div>
    </article>
  )
}

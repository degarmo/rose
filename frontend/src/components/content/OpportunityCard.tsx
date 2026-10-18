import { ArrowRight, CalendarDays, MapPin } from 'lucide-react'
import { Link } from 'react-router'
import type { Opportunity } from '@/lib/api'
import { formatEventDate } from '@/lib/format'
import { Badge, ButtonLink, Card, ImageFrame, type PlaceholderTexture } from '../ui'

const textures: Record<Opportunity['category'], PlaceholderTexture> = {
  class: 'candle',
  workshop: 'silk',
  mentorship: 'shadow',
  volunteer: 'architecture',
  other: 'velvet',
}

export function OpportunityCard({ opportunity, headingLevel = 'h3' }: { opportunity: Opportunity; headingLevel?: 'h2' | 'h3' }) {
  const Heading = headingLevel
  const detailPath = `/education/${opportunity.slug}`
  return (
    <Card as="article" interactive className="h-full">
      <ImageFrame
        remote={opportunity.hero_image}
        alt=""
        ratio="16/9"
        placeholder={textures[opportunity.category]}
        sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
      />
      <div className="flex flex-1 flex-col p-6">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="brass">{opportunity.level_label}</Badge>
          <Badge>{opportunity.category_label}</Badge>
        </div>
        <Heading className="mt-5 text-2xl leading-snug text-fg">
          <Link to={detailPath} className="hover:text-accent">
            {opportunity.title}
          </Link>
        </Heading>
        {(opportunity.starts_at || opportunity.location_label) && (
          <ul className="mt-3 space-y-1.5 text-sm text-fg-muted">
            {opportunity.starts_at && (
              <li className="flex items-center gap-2">
                <CalendarDays aria-hidden="true" className="size-4 text-highlight" />
                <time dateTime={opportunity.starts_at}>{formatEventDate(opportunity.starts_at)}</time>
              </li>
            )}
            {opportunity.location_label && (
              <li className="flex items-center gap-2">
                <MapPin aria-hidden="true" className="size-4 text-highlight" />
                {opportunity.location_label}
              </li>
            )}
          </ul>
        )}
        <p className="mt-4 flex-1 leading-relaxed text-fg-muted">{opportunity.summary}</p>
        <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2">
          {opportunity.cta_label && opportunity.cta_url && (
            <ButtonLink to={opportunity.cta_url}>{opportunity.cta_label}</ButtonLink>
          )}
          <ButtonLink to={detailPath} variant="link" aria-label={`Details about ${opportunity.title}`}>
            Details
            <ArrowRight aria-hidden="true" className="size-4" />
          </ButtonLink>
        </div>
      </div>
    </Card>
  )
}

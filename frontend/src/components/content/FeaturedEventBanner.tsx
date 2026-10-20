import { Link } from 'react-router'
import { api, type EventCategory, type EventSummary } from '@/lib/api'
import { cn } from '@/lib/cn'
import { rsvpBadge } from '@/lib/events'
import { formatLongDate, formatTimeRange } from '@/lib/format'
import { useAsync } from '@/lib/useAsync'
import { Badge, ButtonLink, Chip, ImageFrame } from '../ui'
import { EventImageFallback } from './EventGridCard'

/** The picture's width: about 60% of the banner from 768px (the page stops at 1440px). */
const BANNER_IMAGE_SIZES = '(min-width: 1440px) 820px, (min-width: 768px) 58vw, 100vw'

/**
 * The featured event (one at a time, chosen in the admin; it stops by itself once the evening
 * is over): one large card, the picture on the left from 768px and on top below, with the
 * date, category, time, title, summary, RSVP status and a way in.
 */
export function FeaturedEventBanner({ event, className }: { event: EventSummary; className?: string }) {
  const badge = rsvpBadge(event.rsvp)
  const href = `/events/${event.slug}`
  return (
    <article
      aria-labelledby={`featured-${event.slug}`}
      className={cn('grid overflow-hidden rounded-card border border-border bg-canvas md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]', className)}
    >
      {/* At least 16:10 by its width (the spacer); when the words beside it are taller, the row
          stretches the cell and the picture covers it rather than widening it. */}
      <div className="relative">
        <div aria-hidden="true" className="aspect-[16/10]" />
        {event.hero_image ? (
          <ImageFrame remote={event.hero_image} alt={event.title} fill sizes={BANNER_IMAGE_SIZES} priority placeholder="warm" />
        ) : (
          <EventImageFallback category={event.image_fallback} className="absolute inset-0" />
        )}
        <Badge tone="going" className="absolute left-4 top-4">
          Featured
        </Badge>
      </div>
      <div className="flex min-w-0 flex-col items-start gap-3 p-6 lg:p-10">
        <p className="text-sm font-semibold text-link">
          <time dateTime={event.starts_at}>{formatLongDate(event.starts_at)}</time>
        </p>
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-fg-muted">
          <Chip>{event.category_label}</Chip>
          <span aria-hidden="true">·</span>
          <span>{formatTimeRange(event.starts_at, event.ends_at)}</span>
        </p>
        <h2 id={`featured-${event.slug}`} className="line-clamp-2 font-display text-[1.75rem] leading-[1.15] text-fg lg:text-[2.25rem]">
          <Link to={href} className="hover:text-link">
            {event.title}
          </Link>
        </h2>
        {event.summary && <p className="line-clamp-3 text-fg-muted lg:text-[1.0625rem]">{event.summary}</p>}
        <Badge tone={badge.tone}>{badge.label}</Badge>
        <ButtonLink to={href} className="mt-auto">
          View event
          <span className="sr-only">: {event.title}</span>
        </ButtonLink>
      </div>
    </article>
  )
}

/** The banner for whichever event is featured now in this category, or nothing. */
export function FeaturedEvent({ category = '', className }: { category?: EventCategory | ''; className?: string }) {
  const state = useAsync(() => api.featuredEvent(category), `featured|${category}`)
  if (state.status !== 'success' || state.data.event === null) return null
  return <FeaturedEventBanner event={state.data.event} className={className} />
}

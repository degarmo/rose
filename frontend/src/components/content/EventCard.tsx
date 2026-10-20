import { Link } from 'react-router'
import type { EventSummary } from '@/lib/api'
import { cn } from '@/lib/cn'
import { rsvpBadge } from '@/lib/events'
import { dateParts, formatTimeRange } from '@/lib/format'
import { Badge, Chip } from '../ui'

/**
 * The date block: the day name in rose caps over the day number in Fraunces. `chip` adds the
 * month underneath, for the date laid over an Events grid card's picture.
 */
export function DateColumn({ iso, size = 'card', className }: { iso: string; size?: 'card' | 'chip' | 'compact'; className?: string }) {
  const { weekday, month, day } = dateParts(iso)
  return (
    <div aria-hidden="true" className={cn('shrink-0 text-center leading-none', size === 'compact' ? 'w-11' : size === 'card' && 'w-12 lg:w-14', className)}>
      <div className={cn('font-semibold uppercase text-link', size === 'compact' ? 'text-[0.6875rem]' : 'text-[0.6875rem] tracking-[0.06em] lg:text-xs')}>{weekday}</div>
      <div
        className={cn(
          'mt-1 font-display text-fg',
          size === 'chip' ? 'text-[1.75rem]' : size === 'compact' ? 'text-[1.75rem]' : 'text-[1.875rem] lg:text-[2.25rem]',
        )}
      >
        {day}
      </div>
      {size === 'chip' && <div className="mt-1 text-xs text-fg-muted">{month}</div>}
    </div>
  )
}

/** An event (design: "Event card"), as Home lists the next few. The whole card is one link. */
export function EventCard({ event, headingLevel = 'h3' }: { event: EventSummary; headingLevel?: 'h2' | 'h3' }) {
  const Heading = headingLevel
  const badge = rsvpBadge(event.rsvp)
  return (
    <article className="relative flex h-full gap-4 rounded-card border border-border bg-canvas p-5 lg:gap-5 lg:p-6">
      <DateColumn iso={event.starts_at} />
      <div className="flex min-w-0 flex-1 flex-col items-start gap-1.5 lg:gap-2">
        <Chip className="hidden lg:inline-flex">{event.category_label}</Chip>
        <Heading className="text-xl leading-[1.2] text-fg lg:text-card-title">
          <Link to={`/events/${event.slug}`} className="after:absolute after:inset-0 hover:text-link">
            {event.title}
          </Link>
        </Heading>
        <p className="text-[0.8125rem] text-fg-muted lg:text-sm">
          <span className="lg:hidden">{event.category_label} · </span>
          <time dateTime={event.starts_at}>{formatTimeRange(event.starts_at, event.ends_at)}</time>
        </p>
        <Badge tone={badge.tone} className="lg:mt-1">
          {badge.label}
        </Badge>
      </div>
    </article>
  )
}

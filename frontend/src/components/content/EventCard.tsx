import { Link } from 'react-router'
import type { EventSummary } from '@/lib/api'
import { cn } from '@/lib/cn'
import { rsvpBadge } from '@/lib/events'
import { dateParts, formatTimeRange } from '@/lib/format'
import { Badge, Chip } from '../ui'

/** The date column: the day name in rose caps over the day number in Fraunces. */
export function DateColumn({ iso, size = 'card', className }: { iso: string; size?: 'card' | 'row' | 'compact'; className?: string }) {
  const { weekday, month, day } = dateParts(iso)
  return (
    <div aria-hidden="true" className={cn('shrink-0 text-center leading-none', size === 'compact' ? 'w-11' : 'w-12 lg:w-14', className)}>
      <div className={cn('font-semibold uppercase text-link', size === 'compact' ? 'text-[0.6875rem]' : 'text-[0.6875rem] tracking-[0.06em] lg:text-xs')}>{weekday}</div>
      <div className={cn('mt-1 font-display text-fg', size === 'row' ? 'text-[2.5rem]' : size === 'compact' ? 'text-[1.75rem]' : 'text-[1.875rem] lg:text-[2.25rem]')}>{day}</div>
      {size === 'row' && <div className="mt-1 text-xs text-fg-muted">{month}</div>}
    </div>
  )
}

interface EventCardProps {
  event: EventSummary
  headingLevel?: 'h2' | 'h3'
  /** `card` is the boxed card (home, phones); `row` is the desktop events list row. */
  layout?: 'card' | 'row'
}

/** An event (design: "Event card" and the Events list row). The whole card is one link. */
export function EventCard({ event, headingLevel = 'h3', layout = 'card' }: EventCardProps) {
  const Heading = headingLevel
  const badge = rsvpBadge(event.rsvp)
  const time = <time dateTime={event.starts_at}>{formatTimeRange(event.starts_at, event.ends_at)}</time>
  const title = (
    <Link to={`/events/${event.slug}`} className="after:absolute after:inset-0 hover:text-link">
      {event.title}
    </Link>
  )

  if (layout === 'row') {
    return (
      <article className="relative grid grid-cols-[96px_1fr_200px_160px] items-center gap-8 border-t border-border py-6">
        <DateColumn iso={event.starts_at} size="row" className="w-auto" />
        <div className="flex min-w-0 flex-col gap-1.5">
          <div className="flex flex-wrap items-center gap-3">
            <Heading className="text-[1.625rem] leading-[1.2] text-fg">{title}</Heading>
            <Chip>{event.category_label}</Chip>
          </div>
          {event.summary && <p className="text-fg-muted">{event.summary}</p>}
        </div>
        <p className="text-sm text-fg-muted">{time}</p>
        <Badge tone={badge.tone} className="justify-self-end px-3.5 py-1.5">
          {badge.label}
        </Badge>
      </article>
    )
  }

  return (
    <article className="relative flex h-full gap-4 rounded-card border border-border bg-canvas p-5 lg:gap-5 lg:p-6">
      <DateColumn iso={event.starts_at} />
      <div className="flex min-w-0 flex-1 flex-col items-start gap-1.5 lg:gap-2">
        <Chip className="hidden lg:inline-flex">{event.category_label}</Chip>
        <Heading className="text-xl leading-[1.2] text-fg lg:text-card-title">{title}</Heading>
        <p className="text-[0.8125rem] text-fg-muted lg:text-sm">
          <span className="lg:hidden">{event.category_label} · </span>
          {time}
        </p>
        <Badge tone={badge.tone} className="lg:mt-1">
          {badge.label}
        </Badge>
      </div>
    </article>
  )
}

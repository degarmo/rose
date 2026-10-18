import { Clock, MapPin, Users } from 'lucide-react'
import { Link } from 'react-router'
import type { EventSummary } from '@/lib/api'
import { cn } from '@/lib/cn'
import { rsvpBadge } from '@/lib/events'
import { dateParts, formatTimeRange } from '@/lib/format'
import { Badge, Card } from '../ui'

export function DateBlock({ iso, className }: { iso: string; className?: string }) {
  const { weekday, month, day } = dateParts(iso)
  return (
    <div
      aria-hidden="true"
      className={cn(
        'flex w-16 shrink-0 flex-col items-center self-start rounded-xl border border-highlight/40 bg-surface-sunken py-2 text-center',
        className,
      )}
    >
      <span className="text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-highlight">{weekday}</span>
      <span className="font-display text-3xl leading-none text-fg">{day}</span>
      <span className="text-[0.65rem] uppercase tracking-[0.2em] text-fg-muted">{month}</span>
    </div>
  )
}

export function EventCard({ event, headingLevel = 'h3' }: { event: EventSummary; headingLevel?: 'h2' | 'h3' }) {
  const Heading = headingLevel
  const badge = rsvpBadge(event.rsvp)
  return (
    <Card as="article" interactive className="h-full p-5 sm:p-6">
      <div className="flex gap-5">
        <DateBlock iso={event.starts_at} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{event.category_label}</Badge>
            <Badge tone={badge.tone}>{badge.label}</Badge>
          </div>
          <Heading className="mt-3 text-2xl leading-snug text-fg">
            <Link to={`/events/${event.slug}`} className="after:absolute after:inset-0 hover:text-accent">
              {event.title}
            </Link>
          </Heading>
          <ul className="mt-3 space-y-1.5 text-sm text-fg-muted">
            <li className="flex items-center gap-2">
              <Clock aria-hidden="true" className="size-4 text-highlight" />
              <time dateTime={event.starts_at}>{formatTimeRange(event.starts_at, event.ends_at)}</time>
            </li>
            {event.location_label && (
              <li className="flex items-center gap-2">
                <MapPin aria-hidden="true" className="size-4 text-highlight" />
                {event.location_label}
              </li>
            )}
            {event.attendee_count !== null && (
              <li className="flex items-center gap-2">
                <Users aria-hidden="true" className="size-4 text-highlight" />
                {event.attendee_count} going
              </li>
            )}
          </ul>
        </div>
      </div>
    </Card>
  )
}

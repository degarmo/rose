import { GraduationCap, Lightbulb, Moon, Sparkles, Wine, type LucideIcon } from 'lucide-react'
import { Link } from 'react-router'
import type { EventCategory, EventSummary } from '@/lib/api'
import { cn } from '@/lib/cn'
import { rsvpBadge } from '@/lib/events'
import { formatTimeRange } from '@/lib/format'
import { Badge, Chip, ImageFrame } from '../ui'
import { DateColumn } from './EventCard'

/** The card's picture width at each layout: 3 columns from 1024px (the page stops at 1440px),
 * 2 from 640px, 1 below. */
export const GRID_IMAGE_SIZES = '(min-width: 1440px) 448px, (min-width: 1024px) 31vw, (min-width: 640px) 47vw, 100vw'

/** What stands in for a missing picture: the category's colours and icon, never an empty box. */
const FALLBACKS: Record<EventCategory, { icon: LucideIcon; wash: string }> = {
  education: { icon: GraduationCap, wash: 'from-wash-warm-1 to-wash-rose-1' },
  social: { icon: Wine, wash: 'from-wash-rose-1 to-wash-rose-2' },
  workshop: { icon: Lightbulb, wash: 'from-wash-warm-1 to-wash-warm-2' },
  member_night: { icon: Moon, wash: 'from-wash-rose-1 to-wash-warm-1' },
  special: { icon: Sparkles, wash: 'from-wash-rose-2 to-wash-warm-1' },
}

export function EventImageFallback({ category, className = 'aspect-[4/3]' }: { category: EventCategory; className?: string }) {
  const { icon: Icon, wash } = FALLBACKS[category]
  return (
    <div data-fallback={category} className={cn('relative flex items-center justify-center bg-linear-to-br', wash, className)}>
      <span className="flex size-16 items-center justify-center rounded-full bg-canvas/70">
        <Icon aria-hidden="true" className="size-7 text-link" strokeWidth={1.5} />
      </span>
    </div>
  )
}

/**
 * An event on the Events grid (the owner's override of the list layout; decisions.md): the
 * picture with the date and "Members only" over it, then the category and time, the title,
 * the summary and the RSVP status. The whole card is one link.
 */
export function EventGridCard({ event, priority = false }: { event: EventSummary; priority?: boolean }) {
  const badge = rsvpBadge(event.rsvp)
  return (
    <article
      className={cn(
        'relative flex h-full flex-col overflow-hidden rounded-card border border-border bg-canvas',
        'transition-[translate,box-shadow] duration-200 ease-out hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgb(0_0_0/0.08)]',
        'motion-reduce:transition-none motion-reduce:hover:translate-y-0',
        'has-[a:focus-visible]:ring-2 has-[a:focus-visible]:ring-primary has-[a:focus-visible]:ring-offset-2 has-[a:focus-visible]:ring-offset-canvas',
      )}
    >
      <div className="relative">
        {event.hero_image ? (
          <ImageFrame remote={event.hero_image} alt={event.title} ratio="4/3" sizes={GRID_IMAGE_SIZES} priority={priority} placeholder="warm" />
        ) : (
          <EventImageFallback category={event.image_fallback} />
        )}
        <DateColumn iso={event.starts_at} size="chip" className="absolute left-3 top-3 min-w-14 rounded-xl bg-canvas px-2.5 py-2 shadow-sm" />
        {event.audience === 'members' && (
          <Badge tone="members" className="absolute right-3 top-3">
            Members only
          </Badge>
        )}
      </div>
      <div className="flex flex-1 flex-col items-start gap-2 p-5">
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.8125rem] text-fg-muted">
          <Chip>{event.category_label}</Chip>
          <span aria-hidden="true">·</span>
          <time dateTime={event.starts_at}>{formatTimeRange(event.starts_at, event.ends_at)}</time>
        </p>
        <h2 className="line-clamp-2 font-display text-card-title text-fg">
          <Link to={`/events/${event.slug}`} className="outline-none after:absolute after:inset-0 hover:text-link">
            {event.title}
          </Link>
        </h2>
        {event.summary && <p className="line-clamp-2 text-sm text-fg-muted">{event.summary}</p>}
        <Badge tone={badge.tone} className="mt-auto">
          {badge.label}
        </Badge>
      </div>
    </article>
  )
}

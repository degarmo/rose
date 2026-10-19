import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import type { EventSummary } from '@/lib/api'
import { monthGrid, monthKey, shiftMonth, type MonthRef } from '@/lib/calendar'
import { cn } from '@/lib/cn'
import { rsvpBadge } from '@/lib/events'
import { chicagoDateKey, formatLongDate, formatTimeRange } from '@/lib/format'
import { Badge } from '../ui'
import { DateColumn } from './EventCard'

const WEEKDAYS = [
  ['S', 'Sunday'],
  ['M', 'Monday'],
  ['T', 'Tuesday'],
  ['W', 'Wednesday'],
  ['T', 'Thursday'],
  ['F', 'Friday'],
  ['S', 'Saturday'],
] as const

const monthTitle = new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' })

interface MonthCalendarProps {
  month: MonthRef
  events: EventSummary[]
  onMonthChange: (month: MonthRef) => void
}

/** A compact event card for the chosen day (design: Events · phone, under the month). */
function DayEvent({ event }: { event: EventSummary }) {
  const badge = rsvpBadge(event.rsvp)
  return (
    <li className="relative flex items-center gap-4 rounded-card border border-border bg-canvas p-4">
      <DateColumn iso={event.starts_at} size="compact" />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <h3 className="text-[1.1875rem] leading-[1.2] text-fg">
          <Link to={`/events/${event.slug}`} className="after:absolute after:inset-0 hover:text-link">
            {event.title}
          </Link>
        </h3>
        <p className="text-[0.8125rem] text-fg-muted">
          {event.category_label} · {formatTimeRange(event.starts_at, event.ends_at)}
        </p>
      </div>
      <Badge tone={badge.tone}>{badge.label}</Badge>
    </li>
  )
}

/**
 * The month view (design: "Events · phone (month view)"): a seven-column grid of days with
 * a rose dot under each day that has events; choosing a day lists its events below.
 */
export function MonthCalendar({ month, events, onMonthChange }: MonthCalendarProps) {
  const days = monthGrid(month)
  const [today] = useState(() => chicagoDateKey(new Date()))
  const byDay = new Map<string, EventSummary[]>()
  for (const event of events) {
    const key = chicagoDateKey(event.starts_at)
    byDay.set(key, [...(byDay.get(key) ?? []), event])
  }
  const currentPrefix = monthKey(month)
  const firstWithEvents = days.find((key) => key.startsWith(currentPrefix) && key >= today && byDay.has(key))
  const [chosen, setChosen] = useState<string | null>(null)
  const selected = chosen?.startsWith(currentPrefix) ? chosen : (firstWithEvents ?? (today.startsWith(currentPrefix) ? today : null))
  const selectedEvents = selected ? (byDay.get(selected) ?? []) : []
  // Trailing weeks that hold no day of this month are left out.
  const visible = days.slice(0, Math.ceil((days.findLastIndex((key) => key.startsWith(currentPrefix)) + 1) / 7) * 7)

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,420px)_1fr] lg:gap-12">
      <div>
        <div className="mb-2 flex items-center justify-between">
          <button type="button" onClick={() => onMonthChange(shiftMonth(month, -1))} className="inline-flex size-10 items-center justify-center text-fg-muted hover:text-fg">
            <ChevronLeft aria-hidden="true" strokeWidth={2} className="size-[18px]" />
            <span className="sr-only">Previous month</span>
          </button>
          <h2 className="font-sans text-[0.9375rem] font-semibold text-fg" aria-live="polite">
            {monthTitle.format(new Date(Date.UTC(month.year, month.month, 1)))}
          </h2>
          <button type="button" onClick={() => onMonthChange(shiftMonth(month, 1))} className="inline-flex size-10 items-center justify-center text-fg-muted hover:text-fg">
            <ChevronRight aria-hidden="true" strokeWidth={2} className="size-[18px]" />
            <span className="sr-only">Next month</span>
          </button>
        </div>
        <div aria-hidden="true" className="grid grid-cols-7 gap-1 text-center text-xs font-semibold text-fg-muted">
          {WEEKDAYS.map(([letter, name]) => (
            <div key={name} className="py-1">
              {letter}
            </div>
          ))}
        </div>
        <ol aria-label="Days of the month" className="grid grid-cols-7 gap-1 text-center text-xs">
          {visible.map((key) => {
            const inMonth = key.startsWith(currentPrefix)
            const dayEvents = byDay.get(key) ?? []
            const isSelected = key === selected
            const allFull = dayEvents.length > 0 && dayEvents.every((event) => event.rsvp.state === 'full' || event.rsvp.state === 'closed')
            if (!inMonth) return <li key={key} aria-hidden="true" />
            return (
              <li key={key}>
                <button
                  type="button"
                  onClick={() => setChosen(key)}
                  aria-pressed={isSelected}
                  aria-label={`${formatLongDate(`${key}T18:00:00Z`)}${dayEvents.length ? `, ${dayEvents.length} event${dayEvents.length > 1 ? 's' : ''}` : ''}`}
                  className={cn(
                    'flex aspect-square w-full flex-col items-center justify-center gap-[3px] rounded-app transition-colors',
                    isSelected ? 'bg-tint font-semibold text-tint-fg' : 'text-fg hover:bg-surface',
                    key === today && !isSelected && 'font-semibold',
                  )}
                >
                  {Number(key.slice(8))}
                  {dayEvents.length > 0 && <span aria-hidden="true" className={cn('size-[5px] rounded-full', allFull ? 'bg-fg-muted' : 'bg-primary')} />}
                </button>
              </li>
            )
          })}
        </ol>
      </div>
      <div className="flex flex-col gap-3">
        {selected && <p className="text-[0.8125rem] font-semibold text-fg-muted">{formatLongDate(`${selected}T18:00:00Z`)}</p>}
        {selectedEvents.length > 0 ? (
          <ul className="flex flex-col gap-3">
            {selectedEvents.map((event) => (
              <DayEvent key={event.id} event={event} />
            ))}
          </ul>
        ) : (
          <p className="text-sm text-fg-muted">{selected ? 'Nothing on this day.' : 'Choose a day to see what is on.'}</p>
        )}
      </div>
    </div>
  )
}

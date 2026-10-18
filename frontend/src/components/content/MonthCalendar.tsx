import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import type { EventSummary } from '@/lib/api'
import { monthGrid, monthKey, shiftMonth, type MonthRef } from '@/lib/calendar'
import { cn } from '@/lib/cn'
import { chicagoDateKey } from '@/lib/format'
import { Button } from '../ui'

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

const monthTitle = new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' })

interface MonthCalendarProps {
  month: MonthRef
  events: EventSummary[]
  onMonthChange: (month: MonthRef) => void
}

export function MonthCalendar({ month, events, onMonthChange }: MonthCalendarProps) {
  const days = monthGrid(month)
  const [today] = useState(() => chicagoDateKey(new Date()))
  const byDay = new Map<string, EventSummary[]>()
  for (const event of events) {
    const key = chicagoDateKey(event.starts_at)
    byDay.set(key, [...(byDay.get(key) ?? []), event])
  }
  const currentPrefix = monthKey(month)

  return (
    <div>
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-3xl text-fg" aria-live="polite">
          {monthTitle.format(new Date(Date.UTC(month.year, month.month, 1)))}
        </h2>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={() => onMonthChange(shiftMonth(month, -1))}>
            <ChevronLeft aria-hidden="true" className="size-4" />
            <span className="sr-only">Previous month</span>
          </Button>
          <Button variant="ghost" onClick={() => onMonthChange(shiftMonth(month, 1))}>
            <ChevronRight aria-hidden="true" className="size-4" />
            <span className="sr-only">Next month</span>
          </Button>
        </div>
      </div>

      <div className="mt-6 overflow-hidden rounded-2xl border border-border">
        <div aria-hidden="true" className="grid grid-cols-7 border-b border-border bg-surface-sunken">
          {WEEKDAYS.map((day) => (
            <div key={day} className="py-2 text-center text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-fg-subtle">
              {day}
            </div>
          ))}
        </div>
        <ol aria-label="Days of the month" className="grid grid-cols-7 gap-px bg-border">
          {days.map((key) => {
            const inMonth = key.startsWith(currentPrefix)
            const dayEvents = byDay.get(key) ?? []
            return (
              <li
                key={key}
                aria-label={`${key}${dayEvents.length ? `, ${dayEvents.length} event${dayEvents.length > 1 ? 's' : ''}` : ''}`}
                className={cn(
                  'min-h-14 bg-surface p-1.5 sm:min-h-28 sm:p-2',
                  !inMonth && 'bg-surface-sunken text-fg-subtle',
                )}
              >
                <span
                  className={cn(
                    'inline-flex size-6 items-center justify-center rounded-full text-xs',
                    key === today ? 'bg-primary text-on-primary' : inMonth ? 'text-fg' : 'text-fg-subtle',
                  )}
                >
                  {Number(key.slice(8))}
                </span>
                <ul className="mt-1 flex flex-wrap gap-1 sm:block sm:space-y-1">
                  {dayEvents.map((event) => (
                    <li key={event.id}>
                      <Link
                        to={`/events/${event.slug}`}
                        className="block size-2 rounded-full bg-rose sm:size-auto sm:truncate sm:rounded-md sm:bg-primary-deep sm:px-1.5 sm:py-0.5 sm:text-xs sm:text-fg sm:hover:bg-primary"
                      >
                        <span className="sr-only sm:not-sr-only sm:block sm:truncate">{event.title}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </li>
            )
          })}
        </ol>
      </div>
    </div>
  )
}

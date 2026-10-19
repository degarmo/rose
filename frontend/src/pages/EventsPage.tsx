import { CalendarDays, List } from 'lucide-react'
import { useSearchParams } from 'react-router'
import { EventCard } from '@/components/content/EventCard'
import { MonthCalendar } from '@/components/content/MonthCalendar'
import { PageHero } from '@/components/content/PageHero'
import { Reveal } from '@/components/content/Reveal'
import { EmptyState, ErrorState, SkeletonCards } from '@/components/content/States'
import { FormField, Section, Select } from '@/components/ui'
import { api, type EventCategory } from '@/lib/api'
import { monthGrid, monthKey, parseMonth, type MonthRef } from '@/lib/calendar'
import { cn } from '@/lib/cn'
import { chicagoDateKey } from '@/lib/format'
import { EVENT_CATEGORIES, isEventCategory } from '@/lib/events'
import { useAsync } from '@/lib/useAsync'
import { usePageContent } from '@/lib/pageContent'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

type View = 'list' | 'month'

function ViewToggle({ view, onChange }: { view: View; onChange: (view: View) => void }) {
  const options: Array<{ value: View; label: string; icon: typeof List }> = [
    { value: 'list', label: 'List', icon: List },
    { value: 'month', label: 'Month', icon: CalendarDays },
  ]
  return (
    <div role="group" aria-label="View" className="inline-flex rounded-full border border-border-strong p-1">
      {options.map((option) => {
        const Icon = option.icon
        const active = view === option.value
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.value)}
            className={cn(
              'inline-flex min-h-10 items-center gap-2 rounded-full px-4 text-sm transition-colors',
              active ? 'bg-primary text-on-primary' : 'text-fg-muted hover:text-fg',
            )}
          >
            <Icon aria-hidden="true" className="size-4" />
            {option.label}
          </button>
        )
      })}
    </div>
  )
}

function UpcomingList({ category }: { category: EventCategory | '' }) {
  const state = useAsync(() => api.events(category), `list|${category}`)
  if (state.status === 'loading') return <SkeletonCards count={4} />
  if (state.status === 'error') return <ErrorState title="Events did not load" onRetry={state.retry} />
  if (state.data.length === 0) {
    return <EmptyState title="Nothing scheduled yet" message="New evenings are added every week. Check back soon." />
  }
  return (
    <ul className="grid gap-5 md:grid-cols-2">
      {state.data.map((event, index) => (
        <Reveal as="li" key={event.id} delay={(index % 2) as 0 | 1}>
          <EventCard event={event} headingLevel="h2" />
        </Reveal>
      ))}
    </ul>
  )
}

function MonthView({
  month,
  category,
  onMonthChange,
}: {
  month: MonthRef
  category: EventCategory | ''
  onMonthChange: (month: MonthRef) => void
}) {
  const days = monthGrid(month)
  const state = useAsync(
    () => api.eventCalendar(days[0], days[days.length - 1], category),
    `month|${monthKey(month)}|${category}`,
  )
  const inMonth =
    state.status === 'success'
      ? state.data.filter((event) => chicagoDateKey(event.starts_at).startsWith(monthKey(month)))
      : []

  return (
    <div aria-busy={state.status === 'loading'}>
      <MonthCalendar month={month} events={state.status === 'success' ? state.data : []} onMonthChange={onMonthChange} />
      <div className="mt-10">
        <h2 className="sr-only">Events this month</h2>
        {state.status === 'loading' && <SkeletonCards count={2} />}
        {state.status === 'error' && <ErrorState title="This month did not load" onRetry={state.retry} />}
        {state.status === 'success' && inMonth.length === 0 && (
          <EmptyState title="A quiet month so far" message="Try the next month, or check back soon." />
        )}
        {inMonth.length > 0 && (
          <ul className="grid gap-5 md:grid-cols-2">
            {inMonth.map((event) => (
              <li key={event.id}>
                <EventCard event={event} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export function EventsPage() {
  useDocumentMeta({
    title: 'Events',
    description: 'Education nights, weekend socials and special evenings at the house.',
  })
  const copy = usePageContent('events')
  const [params, setParams] = useSearchParams()
  const view: View = params.get('view') === 'month' ? 'month' : 'list'
  const rawCategory = params.get('category')
  const category: EventCategory | '' = isEventCategory(rawCategory) ? rawCategory : ''
  const month = parseMonth(params.get('month'))

  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value)
      else next.delete(key)
    }
    setParams(next, { replace: true, preventScrollReset: true })
  }

  return (
    <>
      <PageHero copy={copy} image="events-hero.webp" placeholder="candle" />
      <Section spacing="tight" aria-label="Events">
        <div className="flex flex-col gap-5 rounded-2xl border border-border bg-surface p-5 sm:flex-row sm:items-end sm:justify-between">
          <div className="sm:w-72">
            <FormField label="Show" optionalLabel="">
              {(field) => (
                <Select
                  {...field}
                  options={EVENT_CATEGORIES}
                  value={category}
                  onChange={(event) => update({ category: event.target.value || null })}
                />
              )}
            </FormField>
          </div>
          <ViewToggle view={view} onChange={(next) => update({ view: next === 'month' ? 'month' : null })} />
        </div>
        <div className="mt-12" aria-live="polite">
          {view === 'list' ? (
            <UpcomingList category={category} />
          ) : (
            <MonthView month={month} category={category} onMonthChange={(next) => update({ month: monthKey(next) })} />
          )}
        </div>
      </Section>
    </>
  )
}

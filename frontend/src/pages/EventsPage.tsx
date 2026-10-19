import { useSearchParams } from 'react-router'
import { EventCard } from '@/components/content/EventCard'
import { MonthCalendar } from '@/components/content/MonthCalendar'
import { PageHero } from '@/components/content/PageHero'
import { EmptyState, ErrorState, SkeletonCards } from '@/components/content/States'
import { FilterChips, GUTTER, Segmented } from '@/components/ui'
import { api, type EventCategory } from '@/lib/api'
import { monthGrid, monthKey, parseMonth, type MonthRef } from '@/lib/calendar'
import { cn } from '@/lib/cn'
import { chicagoDateKey } from '@/lib/format'
import { EVENT_CATEGORIES, isEventCategory } from '@/lib/events'
import { useAsync } from '@/lib/useAsync'
import { usePageContent } from '@/lib/pageContent'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

type View = 'list' | 'month'

const VIEWS: Array<{ value: View; label: string }> = [
  { value: 'list', label: 'List' },
  { value: 'month', label: 'Month' },
]

// The API's categories as chips; the empty value ("All") clears the filter.
const CATEGORY_CHIPS = EVENT_CATEGORIES.map((option) => ({ value: option.value, label: option.value ? option.label : 'All' }))

/** Ruled rows on desktop (design: Events · desktop); stacked cards on phones. */
function UpcomingList({ category }: { category: EventCategory | '' }) {
  const state = useAsync(() => api.events(category), `list|${category}`)
  if (state.status === 'loading') return <SkeletonCards count={4} />
  if (state.status === 'error') return <ErrorState title="Events did not load" onRetry={state.retry} />
  if (state.data.length === 0) {
    return <EmptyState title="Nothing scheduled yet" message="New evenings are added every week. Check back soon." />
  }
  return (
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1 lg:gap-0">
      {state.data.map((event) => (
        <li key={event.id}>
          <div className="hidden lg:block">
            <EventCard event={event} layout="row" headingLevel="h2" />
          </div>
          <div className="h-full lg:hidden">
            <EventCard event={event} headingLevel="h2" />
          </div>
        </li>
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
  const quiet =
    state.status === 'success' && !state.data.some((event) => chicagoDateKey(event.starts_at).startsWith(monthKey(month)))

  return (
    <div aria-busy={state.status === 'loading'} className="flex flex-col gap-5">
      {state.status === 'error' && <ErrorState title="This month did not load" onRetry={state.retry} />}
      <MonthCalendar month={month} events={state.status === 'success' ? state.data : []} onMonthChange={onMonthChange} />
      {quiet && <p className="text-sm text-fg-muted">A quiet month so far. Try the next month, or check back soon.</p>}
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
      <PageHero
        copy={copy}
        phoneLede={false}
        aside={
          <Segmented
            label="View"
            options={VIEWS}
            value={view}
            onChange={(next) => update({ view: next === 'month' ? 'month' : null })}
            className="shrink-0"
          />
        }
      >
        <FilterChips
          label="Category"
          options={CATEGORY_CHIPS}
          value={category}
          onChange={(next) => update({ category: next || null })}
          className="-mx-5 mt-4 px-5 sm:-mx-8 sm:px-8 lg:mx-0 lg:mt-6 lg:px-0"
        />
      </PageHero>
      <section aria-label="Events" className={cn('mx-auto max-w-[1440px] pb-12 lg:pb-16', GUTTER)}>
        <div aria-live="polite">
          {view === 'list' ? (
            <UpcomingList category={category} />
          ) : (
            <MonthView month={month} category={category} onMonthChange={(next) => update({ month: monthKey(next) })} />
          )}
        </div>
      </section>
    </>
  )
}

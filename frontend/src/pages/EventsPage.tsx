import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { EventGridCard } from '@/components/content/EventGridCard'
import { FeaturedEvent } from '@/components/content/FeaturedEventBanner'
import { MonthCalendar } from '@/components/content/MonthCalendar'
import { PageHero } from '@/components/content/PageHero'
import { EmptyState, ErrorState, SkeletonCards } from '@/components/content/States'
import { Button, FilterChips, GUTTER, Segmented } from '@/components/ui'
import { api, ApiError, type EventCategory, type EventSummary } from '@/lib/api'
import { monthGrid, monthKey, parseMonth, type MonthRef } from '@/lib/calendar'
import { cn } from '@/lib/cn'
import { chicagoDateKey } from '@/lib/format'
import { EVENT_CATEGORIES, isEventCategory } from '@/lib/events'
import { useAsync } from '@/lib/useAsync'
import { usePageContent } from '@/lib/pageContent'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

type View = 'grid' | 'month'

const VIEWS: Array<{ value: View; label: string }> = [
  { value: 'grid', label: 'Grid' },
  { value: 'month', label: 'Month' },
]

/** Three columns by five rows, at every width (the server's page size). */
export const PAGE_SIZE = 15

// The API's categories as chips; the empty value ("All") clears the filter.
const CATEGORY_CHIPS = EVENT_CATEGORIES.map((option) => ({ value: option.value, label: option.value ? option.label : 'All' }))

interface Pages {
  category: EventCategory | ''
  /** One array per page loaded, in order. */
  pages: EventSummary[][]
  count: number
}

/**
 * Pages 1 to `wanted` of the upcoming events, fetching only those not loaded yet (so "Load
 * more" adds one page instead of reloading the rest). Asking past the last page stops there.
 */
function useEventPages(category: EventCategory | '', wanted: number) {
  const [loaded, setLoaded] = useState<Pages | null>(null)
  const [failed, setFailed] = useState<{ category: EventCategory | ''; attempt: number } | null>(null)
  const [attempt, setAttempt] = useState(0)
  const current = loaded?.category === category ? loaded : null

  useEffect(() => {
    let active = true
    const mine = loaded?.category === category ? loaded : null
    const have = mine ? mine.pages : []
    // Enough pages, or every event is already here (an old link asking for more pages).
    if (mine && (have.length >= wanted || have.flat().length >= mine.count)) return
    async function fetchMissing() {
      const pages = [...have]
      let count = mine ? mine.count : 0
      for (let page = have.length + 1; page <= wanted; page += 1) {
        try {
          const result = await api.events(category, page)
          pages.push(result.results)
          count = result.count
          if (!result.next) break
        } catch (error) {
          // Past the last page (an old link, or events since over): stop at what exists.
          if (error instanceof ApiError && error.isNotFound && page > 1) break
          throw error
        }
      }
      return { category, pages, count }
    }
    fetchMissing().then(
      (next) => active && setLoaded(next),
      () => active && setFailed({ category, attempt }),
    )
    return () => {
      active = false
    }
  }, [category, wanted, attempt, loaded])

  const error = failed?.category === category && failed.attempt === attempt
  return { current, error, retry: () => setAttempt((n) => n + 1) }
}

/** Page numbers as plain links, for keyboards, screen readers and sharing: page N shows the
 * first N pages, and following one jumps to where that page begins. */
function PageLinks({ total, current, hrefFor }: { total: number; current: number; hrefFor: (page: number) => string }) {
  if (total < 2) return null
  return (
    <nav aria-label="Pages" className="flex flex-wrap items-center justify-center gap-2 text-sm">
      {Array.from({ length: total }, (_, index) => index + 1).map((page) => (
        <Link
          key={page}
          to={hrefFor(page)}
          aria-current={page === current ? 'page' : undefined}
          aria-label={`Page ${page}`}
          className={cn(
            'inline-flex size-10 items-center justify-center rounded-full border',
            page === current ? 'border-fg bg-fg text-canvas' : 'border-border text-fg hover:border-fg-muted',
          )}
        >
          {page}
        </Link>
      ))}
    </nav>
  )
}

function EventsGrid({
  category,
  page,
  hrefFor,
  onMore,
}: {
  category: EventCategory | ''
  page: number
  hrefFor: (page: number) => string
  onMore: () => void
}) {
  const { current, error, retry } = useEventPages(category, page)
  const pageStarts = useRef<Map<number, HTMLElement>>(new Map())
  // Pages already fetched stay, so Back from ?page=2 shows page 1 without fetching again.
  const visible = current ? current.pages.slice(0, page) : []
  const shownPages = visible.length

  // Arriving at page N (Load more, a page link, the back button): its first card takes focus
  // once it is there, so keyboard and screen reader users land on what is new.
  useEffect(() => {
    if (page > 1 && shownPages >= page) {
      pageStarts.current.get(page)?.querySelector<HTMLElement>('a')?.focus({ preventScroll: false })
    }
  }, [page, shownPages])

  if (error) return <ErrorState title="Events did not load" onRetry={retry} />
  if (!current) return <SkeletonCards count={6} />
  const events = visible.flat()
  if (events.length === 0) {
    return <EmptyState title="Nothing scheduled yet" message="New evenings are added every week. Check back soon." />
  }
  const totalPages = Math.ceil(current.count / PAGE_SIZE)
  return (
    <div className="flex flex-col gap-8">
      <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 lg:gap-6">
        {visible.map((pageEvents, pageIndex) =>
          pageEvents.map((event, index) => (
            <li
              key={event.id}
              ref={index === 0 ? (node) => void (node ? pageStarts.current.set(pageIndex + 1, node) : pageStarts.current.delete(pageIndex + 1)) : undefined}
            >
              <EventGridCard event={event} priority={pageIndex === 0 && index < 3} />
            </li>
          )),
        )}
      </ul>
      <div className="flex flex-col items-center gap-4">
        <p className="text-sm text-fg-muted" aria-live="polite">
          Showing 1–{events.length} of {current.count}
        </p>
        {events.length < current.count && (
          <Button variant="outline" size="lg" onClick={onMore}>
            Load more
          </Button>
        )}
        <PageLinks total={totalPages} current={Math.min(page, shownPages)} hrefFor={hrefFor} />
      </div>
    </div>
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
  const view: View = params.get('view') === 'month' ? 'month' : 'grid'
  const rawCategory = params.get('category')
  const category: EventCategory | '' = isEventCategory(rawCategory) ? rawCategory : ''
  const month = parseMonth(params.get('month'))
  const page = Math.max(1, Number.parseInt(params.get('page') ?? '1', 10) || 1)

  function withChanges(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value)
      else next.delete(key)
    }
    return next
  }

  function update(changes: Record<string, string | null>) {
    setParams(withChanges(changes), { replace: true, preventScrollReset: true })
  }

  /** `?page=N` shows pages 1 to N; it is its own history entry, so Back goes back a page. */
  function hrefFor(target: number) {
    return `?${withChanges({ page: target > 1 ? String(target) : null })}`
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
            onChange={(next) => update({ view: next === 'month' ? 'month' : null, page: null })}
            className="shrink-0"
          />
        }
      >
        {/* Above the filters; the grid leaves it out, and a category without it hides it. */}
        <FeaturedEvent category={category} className="mt-6 lg:mt-8" />
        <FilterChips
          label="Category"
          options={CATEGORY_CHIPS}
          value={category}
          onChange={(next) => update({ category: next || null, page: null })}
          className="-mx-5 mt-4 px-5 sm:-mx-8 sm:px-8 lg:mx-0 lg:mt-6 lg:px-0"
        />
      </PageHero>
      <section aria-label="Events" className={cn('mx-auto max-w-[1440px] pb-12 lg:pb-16', GUTTER)}>
        <div>
          {view === 'grid' ? (
            <EventsGrid
              category={category}
              page={page}
              hrefFor={hrefFor}
              onMore={() => setParams(withChanges({ page: String(page + 1) }), { preventScrollReset: true })}
            />
          ) : (
            <MonthView month={month} category={category} onMonthChange={(next) => update({ month: monthKey(next) })} />
          )}
        </div>
      </section>
    </>
  )
}

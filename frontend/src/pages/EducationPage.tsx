import { useSearchParams } from 'react-router'
import { OpportunityCard } from '@/components/content/OpportunityCard'
import { PageHero } from '@/components/content/PageHero'
import { EmptyState, ErrorState, SkeletonCards } from '@/components/content/States'
import { FilterChips, GUTTER, type SegmentOption } from '@/components/ui'
import { api, type OpportunityCategory, type OpportunityLevel } from '@/lib/api'
import { cn } from '@/lib/cn'
import { useAsync } from '@/lib/useAsync'
import { usePageContent } from '@/lib/pageContent'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

const CATEGORY_OPTIONS: SegmentOption<OpportunityCategory | ''>[] = [
  { value: '', label: 'All' },
  { value: 'class', label: 'Classes' },
  { value: 'workshop', label: 'Workshops' },
  { value: 'mentorship', label: 'Mentorship' },
  { value: 'volunteer', label: 'Volunteering' },
  { value: 'other', label: 'Other' },
]

const LEVEL_OPTIONS: SegmentOption<OpportunityLevel | ''>[] = [
  { value: '', label: 'Any level' },
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
  { value: 'all', label: 'All levels' },
]

function pick<T extends string>(value: string | null, options: SegmentOption<T | ''>[]): T | '' {
  return options.find((option) => option.value === value)?.value ?? ''
}

// Chip rows scroll sideways to the screen edge on phones.
const CHIP_ROW = '-mx-5 px-5 sm:-mx-8 sm:px-8 lg:mx-0 lg:px-0'

/** Education (design: "Education"): two rows of filter chips over a grid of class cards. */
export function EducationPage() {
  useDocumentMeta({
    title: 'Education',
    description: 'Classes, workshops, mentorship and volunteer opportunities for every level of experience.',
  })
  const copy = usePageContent('education')
  const [params, setParams] = useSearchParams()
  const category = pick<OpportunityCategory>(params.get('category'), CATEGORY_OPTIONS)
  const level = pick<OpportunityLevel>(params.get('level'), LEVEL_OPTIONS)
  const state = useAsync(() => api.opportunities({ category, level }), `${category}|${level}`)

  function update(key: 'category' | 'level', value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true, preventScrollReset: true })
  }

  const filtered = Boolean(category || level)

  return (
    <>
      <PageHero copy={copy} phoneLede={false}>
        <div role="search" aria-label="Filter opportunities" className="mt-4 flex flex-col gap-2 lg:mt-6 lg:flex-row lg:gap-6">
          <FilterChips label="Category" options={CATEGORY_OPTIONS} value={category} onChange={(value) => update('category', value)} className={CHIP_ROW} />
          <span aria-hidden="true" className="hidden w-px shrink-0 bg-border lg:block" />
          <FilterChips label="Level" options={LEVEL_OPTIONS} value={level} onChange={(value) => update('level', value)} className={CHIP_ROW} />
        </div>
      </PageHero>

      <section
        aria-label="Opportunities"
        aria-live="polite"
        aria-busy={state.status === 'loading'}
        className={cn('mx-auto max-w-[1440px] pb-12 pt-2 lg:pb-20', GUTTER)}
      >
        {state.status === 'loading' && <SkeletonCards count={6} />}
        {state.status === 'error' && <ErrorState title="Opportunities did not load" onRetry={state.retry} />}
        {state.status === 'success' && state.data.length === 0 && (
          <EmptyState
            title="Nothing matches yet"
            message={filtered ? 'Try a different category or level.' : 'New opportunities are announced each season.'}
          />
        )}
        {state.status === 'success' && state.data.length > 0 && (
          <>
            <p className="sr-only">
              {state.data.length} {state.data.length === 1 ? 'opportunity' : 'opportunities'} shown
            </p>
            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 lg:gap-6">
              {state.data.map((opportunity) => (
                <li key={opportunity.id}>
                  <OpportunityCard opportunity={opportunity} headingLevel="h2" />
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </>
  )
}

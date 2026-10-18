import { X } from 'lucide-react'
import { useSearchParams } from 'react-router'
import { OpportunityCard } from '@/components/content/OpportunityCard'
import { PageHero } from '@/components/content/PageHero'
import { Reveal } from '@/components/content/Reveal'
import { EmptyState, ErrorState, SkeletonCards } from '@/components/content/States'
import { Button, FormField, Section, Select, type SelectOption } from '@/components/ui'
import { api, type OpportunityCategory, type OpportunityLevel } from '@/lib/api'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

const CATEGORY_OPTIONS: SelectOption[] = [
  { value: '', label: 'All categories' },
  { value: 'class', label: 'Classes' },
  { value: 'workshop', label: 'Workshops' },
  { value: 'mentorship', label: 'Mentorship' },
  { value: 'volunteer', label: 'Volunteering' },
  { value: 'other', label: 'Other' },
]

const LEVEL_OPTIONS: SelectOption[] = [
  { value: '', label: 'Any level' },
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
  { value: 'all', label: 'All levels' },
]

function pick<T extends string>(value: string | null, options: SelectOption[]): T | '' {
  return options.some((option) => option.value === value) ? (value as T) : ''
}

export function EducationPage() {
  useDocumentMeta({
    title: 'Education',
    description: 'Classes, workshops, mentorship and volunteer opportunities for every level of experience.',
  })
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
      <PageHero
        eyebrow="Education"
        title="Learn at your own pace."
        lede="Our education program is the heart of the house. Classes are taught by experienced members, and every one of them leaves room for questions."
        image="education-hero.webp"
        placeholder="candle"
      />

      <Section spacing="tight" aria-label="Opportunities">
        <div
          role="search"
          aria-label="Filter opportunities"
          className="grid gap-4 rounded-2xl border border-border bg-surface p-5 sm:grid-cols-[1fr_1fr_auto] sm:items-end"
        >
          <FormField label="Category" optionalLabel="">
            {(field) => (
              <Select
                {...field}
                options={CATEGORY_OPTIONS}
                value={category}
                onChange={(event) => update('category', event.target.value)}
              />
            )}
          </FormField>
          <FormField label="Level" optionalLabel="">
            {(field) => (
              <Select
                {...field}
                options={LEVEL_OPTIONS}
                value={level}
                onChange={(event) => update('level', event.target.value)}
              />
            )}
          </FormField>
          <Button variant="ghost" disabled={!filtered} onClick={() => setParams({}, { replace: true, preventScrollReset: true })}>
            <X aria-hidden="true" className="size-4" />
            Clear
          </Button>
        </div>

        <div className="mt-12" aria-live="polite" aria-busy={state.status === 'loading'}>
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
              <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {state.data.map((opportunity, index) => (
                  <Reveal as="li" key={opportunity.id} delay={(index % 3) as 0 | 1 | 2}>
                    <OpportunityCard opportunity={opportunity} headingLevel="h2" />
                  </Reveal>
                ))}
              </ul>
            </>
          )}
        </div>
      </Section>
    </>
  )
}

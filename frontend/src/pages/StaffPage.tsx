import { Copy, CopyHeading } from '@/components/content/Copy'
import { PageHero } from '@/components/content/PageHero'
import { StaffCard } from '@/components/content/StaffCard'
import { EmptyState, ErrorState, SkeletonCards } from '@/components/content/States'
import { ButtonLink, Card, Section } from '@/components/ui'
import { api } from '@/lib/api'
import { usePageContent } from '@/lib/pageContent'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

const CARD_GRID = 'grid gap-4 sm:grid-cols-2 lg:grid-cols-3 lg:gap-6'

function Team() {
  const state = useAsync(() => api.staff(), 'staff')
  if (state.status === 'loading') return <SkeletonCards count={6} />
  if (state.status === 'error') return <ErrorState title="Our staff did not load" onRetry={state.retry} />
  if (state.data.length === 0) {
    return <EmptyState title="Introductions are on the way" message="Ask for any of our hosts at the door." />
  }
  return (
    <ul className={CARD_GRID}>
      {state.data.map((person) => (
        <li key={person.slug}>
          <StaffCard person={person} />
        </li>
      ))}
    </ul>
  )
}

/** Our staff (no design of its own: a card grid like Education, closing like Home). */
export function StaffPage() {
  useDocumentMeta({
    title: 'Our Staff',
    description: 'The volunteers who host, teach and keep the club running, by the names they choose.',
  })
  const copy = usePageContent('staff')
  const roles = copy.status === 'loading' ? [1, 2, 3] : copy.items('roles')

  return (
    <>
      <PageHero copy={copy} />

      <Section spacing="none" aria-labelledby="team" className="pb-10 pt-4 lg:pb-16 lg:pt-6">
        <CopyHeading copy={copy} prefix="team" id="team" />
        <Team />
      </Section>

      {roles.length > 0 && (
        <Section tone="surface" aria-labelledby="roles">
          <CopyHeading copy={copy} prefix="roles" id="roles" />
          <ul className={CARD_GRID}>
            {roles.map((n) => (
              <li key={n}>
                <Card className="h-full gap-2 p-6 lg:p-8">
                  <Copy copy={copy} k={`roles.${n}.title`} as="h3" className="text-xl leading-[1.2] text-fg lg:text-card-title" />
                  <Copy copy={copy} k={`roles.${n}.body`} lines={2} className="text-sm text-fg-muted lg:text-body" />
                </Card>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section spacing="none" aria-labelledby="join-team" className="py-14 lg:py-24">
        <div className="flex flex-col items-center gap-4 text-center lg:gap-6">
          <Copy
            copy={copy}
            k="cta.title"
            as="h2"
            id="join-team"
            lines={2}
            className="w-full max-w-[640px] text-[2.125rem] font-light leading-[1.1] text-fg lg:text-h2-lg"
          />
          <Copy copy={copy} k="cta.lede" lines={2} className="max-w-[560px] text-fg-muted lg:text-lead" />
          <ButtonLink to="/get-involved/volunteer" size="lg">
            Volunteer with us
          </ButtonLink>
        </div>
      </Section>
    </>
  )
}

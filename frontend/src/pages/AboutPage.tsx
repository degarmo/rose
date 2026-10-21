import { Link } from 'react-router'
import { Copy, CopyHeading } from '@/components/content/Copy'
import { PageHero } from '@/components/content/PageHero'
import { StaffCard } from '@/components/content/StaffCard'
import { ErrorState, SkeletonCards } from '@/components/content/States'
import { ValuesStrip } from '@/components/content/ValuesStrip'
import { Section } from '@/components/ui'
import { api } from '@/lib/api'
import { usePageContent, type PageCopy } from '@/lib/pageContent'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

const STRIP_COUNT = 6

function StaffStrip() {
  const state = useAsync(() => api.staff(), 'staff')
  if (state.status === 'loading') return <SkeletonCards count={3} />
  if (state.status === 'error') return <ErrorState title="Our staff did not load" onRetry={state.retry} />
  if (state.data.length === 0) return null
  return (
    <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6 lg:gap-6">
      {state.data.slice(0, STRIP_COUNT).map((person) => (
        <li key={person.slug}>
          <StaffCard person={person} compact />
        </li>
      ))}
    </ul>
  )
}

// How the club is run: editable words (nonprofit.*, volunteer.*), interface links.
const RUN = [
  { prefix: 'nonprofit', to: '/get-involved/donate', action: 'Ways to give' },
  { prefix: 'volunteer', to: '/get-involved/volunteer', action: 'Volunteer with us' },
]

function HowWeAreRun({ copy }: { copy: PageCopy }) {
  return (
    <ul className="grid gap-3 sm:grid-cols-2 lg:gap-6">
      {RUN.map((item) => (
        <li key={item.prefix} className="flex flex-col gap-1.5 rounded-card bg-surface p-6 lg:gap-3 lg:p-8">
          <Copy copy={copy} k={`${item.prefix}.title`} as="h2" className="text-[1.375rem] leading-[1.2] text-fg lg:text-[1.625rem]" />
          <Copy copy={copy} k={`${item.prefix}.body`} lines={3} className="flex-1 text-sm text-fg-muted lg:text-body" />
          <Link to={item.to} className="self-start text-sm font-semibold text-link hover:text-primary-hover">
            {item.action} <span aria-hidden="true">→</span>
          </Link>
        </li>
      ))}
    </ul>
  )
}

/** About (no design of its own: laid out like Home's "Who we are" and values band). */
export function AboutPage() {
  useDocumentMeta({
    title: 'About',
    description: 'Our mission, our values and the volunteers who keep the club running.',
  })
  const copy = usePageContent('about')

  return (
    <>
      <PageHero copy={copy} slot="about.hero" ratio="5/4" placeholder="warm" />

      <Section rule aria-labelledby="mission">
        <div className="grid gap-3 lg:grid-cols-[1fr_2fr] lg:gap-16">
          <Copy copy={copy} k="mission.title" as="h2" id="mission" className="text-[1.75rem] font-light leading-[1.2] text-fg lg:text-h2" />
          <Copy
            copy={copy}
            k="mission.lede"
            lines={4}
            className="max-w-[680px] lg:text-lead [&>p:first-child]:text-fg"
          />
        </div>
      </Section>

      <Section spacing="none" aria-label="How we are run" className="pb-10 lg:pb-16">
        <HowWeAreRun copy={copy} />
      </Section>

      <ValuesStrip text="long" heading={<Copy copy={copy} k="values.title" as="span" />} />

      <Section aria-labelledby="people">
        <CopyHeading copy={copy} prefix="people" id="people" action={{ to: '/about/staff', label: 'Meet our staff' }} />
        <StaffStrip />
      </Section>
    </>
  )
}

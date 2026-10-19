import { CopyHeading } from '@/components/content/Copy'
import { FAQAccordion } from '@/components/content/FAQAccordion'
import { PageHero } from '@/components/content/PageHero'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { ButtonLink, Section } from '@/components/ui'
import { api } from '@/lib/api'
import { usePageContent } from '@/lib/pageContent'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

function Questions() {
  const state = useAsync(() => api.faqs(), 'faqs')
  if (state.status === 'loading') return <LoadingState label="Loading questions" />
  if (state.status === 'error') return <ErrorState title="Questions did not load" onRetry={state.retry} />
  if (state.data.length === 0) {
    return <EmptyState title="No questions yet" message="Send us yours and we will answer it." />
  }
  return <FAQAccordion items={state.data} />
}

export function FAQPage() {
  useDocumentMeta({
    title: 'FAQ',
    description: 'Answers to the questions people ask most before their first visit.',
  })
  const copy = usePageContent('faq')
  return (
    <>
      <PageHero copy={copy} image="visit-hero.webp" placeholder="shadow" />
      <Section width="narrow" aria-label="Questions">
        <Questions />
      </Section>
      <Section tone="sunken" width="narrow" aria-labelledby="still">
        <CopyHeading copy={copy} prefix="cta" id="still" />
        <div className="mt-10 flex flex-col gap-3 sm:flex-row">
          <ButtonLink to="/contact" size="lg">
            Ask us
          </ButtonLink>
          <ButtonLink to="/visit" size="lg" variant="ghost">
            Plan your visit
          </ButtonLink>
        </div>
      </Section>
    </>
  )
}

import { Copy } from '@/components/content/Copy'
import { FAQAccordion } from '@/components/content/FAQAccordion'
import { PageHero } from '@/components/content/PageHero'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { ButtonLink, GUTTER } from '@/components/ui'
import { api } from '@/lib/api'
import { cn } from '@/lib/cn'
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

/** FAQ (no design of its own; the questions as on Plan Your Visit, "Questions we get"). */
export function FAQPage() {
  useDocumentMeta({
    title: 'FAQ',
    description: 'Answers to the questions people ask most before their first visit.',
  })
  const copy = usePageContent('faq')
  return (
    <>
      <PageHero copy={copy} />
      <div className={cn('mx-auto flex max-w-[1440px] flex-col gap-8 pb-12 pt-4 lg:gap-12 lg:pb-20 lg:pt-6', GUTTER)}>
        <section aria-label="Questions" className="max-w-[860px]">
          <Questions />
        </section>
        <section aria-labelledby="still" className="flex max-w-[860px] flex-col items-start gap-2 rounded-card bg-blush p-5 lg:p-8">
          <Copy copy={copy} k="cta.title" as="h2" id="still" className="text-xl leading-[1.3] text-fg lg:text-2xl" />
          <Copy copy={copy} k="cta.lede" lines={2} className="text-sm leading-[1.6] text-fg-muted-tint lg:text-[0.9375rem]" />
          <div className="mt-3 flex flex-wrap gap-2">
            <ButtonLink to="/contact">Ask us</ButtonLink>
            <ButtonLink to="/visit" variant="secondary">
              Plan your visit
            </ButtonLink>
          </div>
        </section>
      </div>
    </>
  )
}

import { Copy } from '@/components/content/Copy'
import { PageHero } from '@/components/content/PageHero'
import { ButtonLink, GUTTER } from '@/components/ui'
import { cn } from '@/lib/cn'
import { usePageContent } from '@/lib/pageContent'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/** House rules (no design of its own; long text set like the Join agreement: 600 headings, muted body). */
export function HouseRulesPage() {
  useDocumentMeta({
    title: 'House Rules',
    description: 'The agreements everyone keeps at the house, so every evening is safe and comfortable.',
  })
  const copy = usePageContent('rules')
  const sections = copy.status === 'loading' ? [1, 2, 3] : copy.items('rules')
  return (
    <>
      <PageHero copy={copy} />
      <div className={cn('mx-auto flex max-w-[1440px] flex-col gap-10 pb-12 pt-4 lg:gap-14 lg:pb-20 lg:pt-6', GUTTER)}>
        <section aria-label="House rules" className="flex max-w-[720px] flex-col gap-6 lg:gap-7">
          <Copy copy={copy} k="intro" lines={2} className="text-fg lg:text-[1.0625rem]" />
          {sections.map((n) => (
            <section key={n} aria-labelledby={`rule-${n}`} className="flex flex-col gap-1">
              <Copy copy={copy} k={`rules.${n}.title`} as="h2" id={`rule-${n}`} className="font-sans text-base font-semibold text-fg" />
              <Copy copy={copy} k={`rules.${n}.body`} lines={3} className="text-fg-muted" />
            </section>
          ))}
        </section>
        <section aria-labelledby="rules-help" className="flex max-w-[720px] flex-col items-start gap-2 rounded-card bg-blush p-5 lg:p-8">
          <Copy copy={copy} k="help.title" as="h2" id="rules-help" className="text-xl leading-[1.3] text-fg lg:text-2xl" />
          <Copy copy={copy} k="help.lede" lines={2} className="text-sm leading-[1.6] text-fg-muted-tint lg:text-[0.9375rem]" />
          <div className="mt-3 flex flex-wrap gap-2">
            <ButtonLink to="/contact">Contact us</ButtonLink>
            <ButtonLink to="/faq" variant="secondary">
              Read the FAQ
            </ButtonLink>
          </div>
        </section>
      </div>
    </>
  )
}

import { Copy } from '@/components/content/Copy'
import { PageHero } from '@/components/content/PageHero'
import { GUTTER } from '@/components/ui'
import { cn } from '@/lib/cn'
import { usePageContent } from '@/lib/pageContent'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/** Privacy (no design of its own; long text set like the Join agreement: 600 headings, muted body). */
export function PrivacyPage() {
  useDocumentMeta({
    title: 'Privacy',
    description: 'What we collect, what is never public, and how to ask us to delete your information.',
  })
  const copy = usePageContent('privacy')
  const blocks = copy.status === 'loading' ? [1, 2, 3] : copy.items('blocks')

  return (
    <>
      <PageHero copy={copy} />
      <div className={cn('mx-auto max-w-[1440px] pb-12 pt-4 lg:pb-20 lg:pt-6', GUTTER)}>
        <div className="flex max-w-[720px] flex-col gap-6 lg:gap-8">
          {blocks.map((n) => (
            <section key={n} aria-labelledby={`privacy-${n}`} className="flex flex-col gap-1.5">
              <Copy copy={copy} k={`blocks.${n}.title`} as="h2" id={`privacy-${n}`} className="font-sans text-base font-semibold text-fg" />
              <Copy copy={copy} k={`blocks.${n}.body`} lines={4} className="text-fg-muted" />
            </section>
          ))}
        </div>
      </div>
    </>
  )
}

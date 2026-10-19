import type { ReactNode } from 'react'
import { GUTTER } from '@/components/ui'
import { cn } from '@/lib/cn'
import { valueNumbers } from '@/content/values'
import { usePageContent } from '@/lib/pageContent'
import { Copy } from './Copy'

interface ValuesStripProps {
  /** `short` lines on the home page; the `long` paragraphs on About. */
  text?: 'short' | 'long'
  /** A visible section title; without one the band keeps a hidden "Our values" heading. */
  heading?: ReactNode
  id?: string
}

/**
 * The values band (design: Home, the oxblood band): four titles in Fraunces over
 * pale rose text, four across on desktop and two across on phones.
 */
export function ValuesStrip({ text = 'short', heading, id = 'values' }: ValuesStripProps) {
  const copy = usePageContent('values')
  const long = text === 'long'
  return (
    <section aria-labelledby={id} className="bg-oxblood py-10 text-white lg:py-14">
      <div className={cn('mx-auto max-w-[1440px]', GUTTER)}>
        {heading ? (
          <h2 id={id} className="mb-8 text-[1.75rem] font-light leading-[1.2] lg:mb-10 lg:text-h2">
            {heading}
          </h2>
        ) : (
          <h2 id={id} className="sr-only">
            Our values
          </h2>
        )}
        <ul className={cn('grid gap-6 lg:grid-cols-4 lg:gap-12', long ? 'sm:grid-cols-2 sm:gap-x-10 sm:gap-y-8' : 'grid-cols-2')}>
          {valueNumbers(copy).map((n) => (
            <li key={n}>
              <Copy copy={copy} k={`values.${n}.title`} as="h3" className="mb-1 text-[1.375rem] leading-[1.2] lg:mb-2 lg:text-[1.625rem]" />
              <Copy copy={copy} k={`values.${n}.${text}`} lines={long ? 4 : 2} className="text-sm text-on-oxblood lg:text-body" />
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

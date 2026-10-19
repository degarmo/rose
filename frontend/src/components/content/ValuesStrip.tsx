import { valueIcon } from '@/content/values'
import { usePageContent } from '@/lib/pageContent'
import { Copy } from './Copy'
import { Reveal } from './Reveal'

export function ValuesStrip() {
  const copy = usePageContent('values')
  const items = copy.status === 'loading' ? [1, 2, 3, 4] : copy.items('values')
  return (
    <ul className="grid gap-px overflow-hidden rounded-2xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-4">
      {items.map((n, index) => {
        const Icon = valueIcon(n)
        return (
          <Reveal as="li" key={n} delay={(index % 4) as 0 | 1 | 2 | 3} className="bg-surface p-8">
            <Icon aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
            <Copy copy={copy} k={`values.${n}.title`} as="h3" className="mt-6 text-2xl text-fg" />
            <Copy copy={copy} k={`values.${n}.short`} lines={2} className="mt-3 leading-relaxed text-fg-muted" />
          </Reveal>
        )
      })}
    </ul>
  )
}

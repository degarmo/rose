import { VALUES } from '@/content/values'
import { Reveal } from './Reveal'

export function ValuesStrip() {
  return (
    <ul className="grid gap-px overflow-hidden rounded-2xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-4">
      {VALUES.map((value, index) => {
        const Icon = value.icon
        return (
          <Reveal as="li" key={value.title} delay={(index % 4) as 0 | 1 | 2 | 3} className="bg-surface p-8">
            <Icon aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
            <h3 className="mt-6 text-2xl text-fg">{value.title}</h3>
            <p className="mt-3 leading-relaxed text-fg-muted">{value.short}</p>
          </Reveal>
        )
      })}
    </ul>
  )
}

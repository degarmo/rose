import { Plus } from 'lucide-react'
import type { FAQItem } from '@/lib/api'

/** Native details/summary: keyboard and screen-reader friendly without extra script. */
export function FAQAccordion({ items }: { items: FAQItem[] }) {
  return (
    <div className="divide-y divide-border border-y border-border">
      {items.map((item) => (
        <details key={item.id} className="group">
          <summary className="flex min-h-16 cursor-pointer list-none items-center justify-between gap-6 py-5 text-left text-lg text-fg transition-colors hover:text-accent [&::-webkit-details-marker]:hidden">
            <span className="font-display text-xl">{item.question}</span>
            <Plus
              aria-hidden="true"
              className="size-5 shrink-0 text-highlight transition-transform duration-500 ease-velvet group-open:rotate-45"
            />
          </summary>
          <p className="max-w-2xl pb-6 leading-relaxed text-fg-muted">{item.answer}</p>
        </details>
      ))}
    </div>
  )
}

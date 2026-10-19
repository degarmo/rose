import { ChevronDown } from 'lucide-react'
import type { FAQItem } from '@/lib/api'

/**
 * Questions and answers (design: Plan Your Visit, "Questions we get"): ruled rows, the
 * question at 16/600 with a chevron that turns when open. Native details/summary, so it
 * works by keyboard and with screen readers without extra script.
 */
export function FAQAccordion({ items, openFirst = false }: { items: FAQItem[]; /** Start with the first answer showing (design: Plan Your Visit). */ openFirst?: boolean }) {
  return (
    <div className="border-b border-border">
      {items.map((item, index) => (
        <details key={item.id} open={openFirst && index === 0} className="group border-t border-border">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 py-4 text-[0.9375rem] font-semibold text-fg lg:py-5 lg:text-base [&::-webkit-details-marker]:hidden">
            {item.question}
            <ChevronDown aria-hidden="true" strokeWidth={2} className="size-3.5 shrink-0 text-fg-muted transition-transform duration-150 group-open:rotate-180" />
          </summary>
          <p className="max-w-[680px] pb-4 text-sm text-fg-muted lg:pb-5 lg:text-[0.9375rem]">{item.answer}</p>
        </details>
      ))}
    </div>
  )
}

import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

/**
 * One term and value in a <dl>. The dt and dd are direct children of the item's
 * div (valid HTML for screen readers); the icon sits inside the dt.
 */
export function DetailItem({ icon: Icon, label, children }: { icon: LucideIcon; label: string; children: ReactNode }) {
  return (
    <div className="relative pl-8">
      <dt className="text-xs font-semibold uppercase tracking-[0.2em] text-fg-subtle">
        <Icon aria-hidden="true" className="absolute left-0 top-0.5 size-5 text-highlight" />
        {label}
      </dt>
      <dd className="mt-1 text-fg">{children}</dd>
    </div>
  )
}

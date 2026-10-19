import type { ReactNode } from 'react'

/**
 * One term and value in a <dl> (design: Event detail, "When / Where"): the label in muted
 * text above a 600 value on desktop, the two on one line on phones ("When Thu, Oct 22").
 */
export function DetailItem({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap gap-x-1.5 lg:flex-col">
      <dt className="text-fg-muted">{label}</dt>
      <dd className="font-semibold text-fg">{children}</dd>
    </div>
  )
}

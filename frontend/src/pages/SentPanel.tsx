import { Check } from 'lucide-react'
import type { ReactNode, Ref } from 'react'
import { cn } from '@/lib/cn'

/** The panel's 44px outline pill ("Back to home"). */
export const SENT_ACTION =
  'inline-flex h-11 items-center justify-center rounded-full border border-fg bg-canvas px-6 text-sm font-semibold text-fg transition-colors hover:bg-surface'

interface SentPanelProps {
  title?: ReactNode
  /** Receives focus once the panel appears, so screen readers hear the outcome. */
  headingRef?: Ref<HTMLHeadingElement>
  headingLevel?: 'h1' | 'h2'
  children?: ReactNode
  actions?: ReactNode
  className?: string
}

/**
 * The confirmation after a form is sent (design: "Contact · phone (success)"): a blush
 * panel with a white, rose-ringed check, a Fraunces line, a muted note and a way on.
 */
export function SentPanel({ title, headingRef, headingLevel: Heading = 'h2', children, actions, className }: SentPanelProps) {
  return (
    <div role="status" className={cn('flex flex-col items-center gap-3 rounded-panel bg-blush px-6 py-8 text-center', className)}>
      <span className="flex size-14 items-center justify-center rounded-full border-[1.5px] border-primary bg-canvas text-link">
        <Check aria-hidden="true" className="size-6" strokeWidth={1.8} />
      </span>
      {title && (
        <Heading ref={headingRef} tabIndex={-1} className="text-[1.625rem] leading-[1.15] text-fg focus:outline-none">
          {title}
        </Heading>
      )}
      {children && <div className="max-w-[440px] text-sm text-fg-muted-tint">{children}</div>}
      {actions && <div className="mt-2 flex flex-wrap items-center justify-center gap-3">{actions}</div>}
    </div>
  )
}

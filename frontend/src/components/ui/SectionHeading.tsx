import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { cn } from '@/lib/cn'

interface SectionHeadingProps {
  title: ReactNode
  /** A rose link on the right, like "All events". */
  action?: { to: string; label: string }
  lede?: ReactNode
  id?: string
  className?: string
}

/** A section title in Fraunces 300 (32px, 28 on phones), with an optional link at the end. */
export function SectionHeading({ title, action, lede, id, className }: SectionHeadingProps) {
  return (
    <header className={cn('mb-4 lg:mb-8', className)}>
      <div className="flex items-baseline justify-between gap-4">
        <h2 id={id} className="text-[1.75rem] font-light leading-[1.2] text-fg lg:text-h2">
          {title}
        </h2>
        {action && (
          <Link to={action.to} className="shrink-0 text-sm font-semibold text-link hover:text-primary-hover">
            {action.label}
          </Link>
        )}
      </div>
      {lede && <div className="mt-2 max-w-[680px] text-fg-muted lg:text-lead">{lede}</div>}
    </header>
  )
}

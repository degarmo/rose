import { Link } from 'react-router'
import { cn } from '@/lib/cn'

/** "Rose" in Fraunces, oxblood: the only use of that colour (design system: "Oxblood"). */
export function Wordmark({ onNavigate, className }: { onNavigate?: () => void; className?: string }) {
  return (
    <Link to="/" onClick={onNavigate} className={cn('inline-flex min-h-10 items-center font-display text-[1.625rem] leading-none text-wordmark xl:text-[1.75rem]', className)}>
      Rose
    </Link>
  )
}

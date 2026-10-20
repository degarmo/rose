import { Link } from 'react-router'
import { cn } from '@/lib/cn'
import { config } from '@/lib/config'

/**
 * The club's name in Fraunces, oxblood: the only use of that colour (design system:
 * "Oxblood"). Phones get the short form; the full name from the small breakpoint up.
 */
export function Wordmark({ onNavigate, className }: { onNavigate?: () => void; className?: string }) {
  return (
    <Link to="/" onClick={onNavigate} className={cn('inline-flex min-h-10 items-center whitespace-nowrap font-display text-[1.375rem] leading-none text-wordmark sm:text-[1.625rem] xl:text-[1.75rem]', className)}>
      <span className="sm:hidden">{config.shortName}</span>
      <span className="hidden sm:inline">{config.displayName}</span>
    </Link>
  )
}

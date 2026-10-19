import { LogOut } from 'lucide-react'
import { cn } from '@/lib/cn'
import { leaveNow, quickExitUrl } from '@/lib/quickExit'

interface QuickExitProps {
  /** `pill` sits in the header and footer; `floating` is pinned to the corner where there is no header. */
  variant?: 'pill' | 'floating'
  className?: string
}

/**
 * The Leave control (design system: "Leave"): a 40px bordered pill in muted text with the
 * LogOut icon, 36px on phones. It replaces this page in the history and goes to a neutral site.
 */
export function QuickExit({ variant = 'pill', className }: QuickExitProps) {
  return (
    <a
      href={quickExitUrl()}
      onClick={(event) => {
        event.preventDefault()
        leaveNow()
      }}
      rel="noreferrer"
      title="Leave this site now. Shortcut: press Esc twice."
      className={cn(
        'inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full border border-border bg-canvas px-3.5 text-[0.8125rem] font-semibold text-fg-muted transition-colors duration-150 hover:border-fg-muted hover:text-fg sm:h-10 sm:px-4 sm:text-sm print:hidden',
        variant === 'floating' && 'fixed bottom-6 right-6 z-40',
        className,
      )}
    >
      <LogOut aria-hidden="true" className="size-3.5 sm:size-4" strokeWidth={1.8} />
      Leave
      <span className="sr-only"> this site now. Shortcut: press Escape twice.</span>
    </a>
  )
}

import { LogOut } from 'lucide-react'
import { cn } from '@/lib/cn'
import { leaveNow, quickExitUrl } from '@/lib/quickExit'

interface QuickExitProps {
  variant?: 'floating' | 'inline' | 'compact'
  className?: string
}

export function QuickExit({ variant = 'floating', className }: QuickExitProps) {
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
        'group inline-flex min-h-11 items-center gap-2 rounded-full border text-sm font-semibold tracking-wide transition-colors duration-300 print:hidden',
        variant === 'floating' &&
          'fixed bottom-6 right-6 z-40 border-highlight/60 bg-canvas/90 px-4 text-fg shadow-lg shadow-black/15 backdrop-blur hover:bg-primary hover:text-on-primary',
        variant === 'inline' && 'border-border-strong px-4 text-fg hover:border-highlight hover:bg-primary hover:text-on-primary',
        variant === 'compact' && 'border-highlight/60 px-3.5 text-fg hover:bg-primary hover:text-on-primary',
        className,
      )}
    >
      <LogOut aria-hidden="true" className="size-4 text-highlight group-hover:text-on-primary" />
      Leave
      <span className="sr-only"> this site now. Shortcut: press Escape twice.</span>
    </a>
  )
}

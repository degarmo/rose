import { LogOut } from 'lucide-react'
import type { ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'
import { leaveNow, quickExitUrl } from '@/lib/quickExit'
import { variants, type Variant } from './ui'

/** The app's button: 32px tall, 8px corners, weight 600. */
export function IgButton({
  variant = 'primary',
  className,
  type = 'button',
  ...rest
}: { variant?: Variant } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex h-8 items-center justify-center gap-1.5 rounded-lg text-sm font-semibold transition-colors duration-150 ease-out disabled:cursor-not-allowed disabled:opacity-50',
        variants[variant],
        className,
      )}
      {...rest}
    />
  )
}

/** "Rose" in Fraunces, oxblood (lighter in dark appearance). The only Fraunces in the app. */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span aria-hidden="true" className={cn('font-wordmark text-[1.75rem] leading-none tracking-wide text-wordmark', className)}>
      Rose
    </span>
  )
}

/** The small rose mark used where the wordmark does not fit, and as the club's avatar. */
export function RoseMark({ className }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'inline-flex shrink-0 items-center justify-center rounded-full border-[1.5px] border-wordmark font-wordmark leading-none text-wordmark',
        className,
      )}
    >
      R
    </span>
  )
}

/** The quick exit as an icon, for layers that cover the app's own (stories, Create, the post view). */
export function LeaveIcon({ className }: { className?: string }) {
  return (
    <a
      href={quickExitUrl()}
      onClick={(event) => {
        event.preventDefault()
        leaveNow()
      }}
      rel="noreferrer"
      title="Leave this site now. Shortcut: press Esc twice."
      className={cn('inline-flex size-10 items-center justify-center', className)}
    >
      <LogOut aria-hidden="true" className="size-6" strokeWidth={2.5} />
      <span className="sr-only">Leave this site now. Shortcut: press Escape twice.</span>
    </a>
  )
}

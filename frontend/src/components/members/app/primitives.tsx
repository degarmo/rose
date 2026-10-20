import { LogOut } from 'lucide-react'
import type { ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'
import { config } from '@/lib/config'
import { leaveNow, quickExitUrl } from '@/lib/quickExit'
import { appButtonClasses, type Variant } from './ui'

/** The app's button: 32px tall, 8px corners, weight 600. */
export function AppButton({
  variant = 'primary',
  className,
  type = 'button',
  ...rest
}: { variant?: Variant } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type={type} className={appButtonClasses(variant, className)} {...rest} />
}

/** The club's name in Fraunces, oxblood (lighter in dark appearance). The only Fraunces in the app. */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span aria-hidden="true" className={cn('whitespace-nowrap font-serif text-[1.75rem] leading-none text-wordmark', className)}>
      {config.siteName}
    </span>
  )
}

/** The club's avatar: "R" on oxblood (design: the "Rose" story and club posts). */
export function RoseMark({ className }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'inline-flex shrink-0 items-center justify-center rounded-full bg-oxblood font-serif leading-none text-on-oxblood',
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
      <LogOut aria-hidden="true" className="size-6" strokeWidth={1.8} />
      <span className="sr-only">Leave this site now. Shortcut: press Escape twice.</span>
    </a>
  )
}

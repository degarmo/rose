import { ChevronRight, MailWarning, type LucideIcon } from 'lucide-react'
import { useId, useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { AppButton } from '@/components/members/app/primitives'
import { appButtonClasses, ICON } from '@/components/members/app/ui'
import { Switch, useToast } from '@/components/ui'
import { api } from '@/lib/api'
import { cn } from '@/lib/cn'

/** One settings row (design: 56px, a 24px icon, the label at 600 over an optional 12px line). */
export const ROW = 'flex min-h-14 w-full items-center gap-4 border-b border-border py-2 text-left last:border-b-0'

export function RowText({ label, sub, danger = false }: { label: ReactNode; sub?: ReactNode; danger?: boolean }) {
  return (
    <span className="min-w-0 flex-1">
      <span className={cn('block font-semibold', danger ? 'text-danger' : 'text-fg')}>{label}</span>
      {sub && <span className="block text-meta text-fg-muted">{sub}</span>}
    </span>
  )
}

export function RowIcon({ icon: Icon, danger = false }: { icon: LucideIcon; danger?: boolean }) {
  return <Icon aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} className={cn('shrink-0', danger ? 'text-danger' : 'text-fg')} />
}

export const CHEVRON = <ChevronRight aria-hidden="true" size={20} strokeWidth={ICON.stroke} className="shrink-0 text-fg-muted" />

export function LinkRow({
  icon,
  label,
  sub,
  to,
  value,
  danger,
}: {
  icon: LucideIcon
  label: string
  sub?: ReactNode
  to: string
  value?: string
  danger?: boolean
}) {
  return (
    <li>
      <Link to={to} className={cn(ROW, 'px-1 hover:bg-surface')}>
        <RowIcon icon={icon} danger={danger} />
        <RowText label={label} sub={sub} danger={danger} />
        {value && <span className="shrink-0 text-fg-muted">{value}</span>}
        {CHEVRON}
      </Link>
    </li>
  )
}

export function ButtonRow({
  icon,
  label,
  sub,
  onClick,
  danger,
  disabled,
}: {
  icon: LucideIcon
  label: string
  sub?: ReactNode
  onClick: () => void
  danger?: boolean
  disabled?: boolean
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        className={cn(ROW, 'px-1 hover:bg-surface disabled:cursor-default disabled:opacity-60 disabled:hover:bg-transparent')}
      >
        <RowIcon icon={icon} danger={danger} />
        <RowText label={label} sub={sub} danger={danger} />
        {CHEVRON}
      </button>
    </li>
  )
}

/** A row with a switch on the right; the words are its label. */
export function SwitchRow({
  icon,
  label,
  sub,
  checked,
  disabled,
  locked,
  onChange,
}: {
  icon: LucideIcon
  label: string
  sub?: ReactNode
  checked: boolean
  disabled?: boolean
  locked?: boolean
  onChange: (value: boolean) => void
}) {
  const id = useId()
  return (
    <li className={cn(ROW, 'px-1')}>
      <RowIcon icon={icon} />
      <label htmlFor={id} className={cn('min-w-0 flex-1', !locked && 'cursor-pointer')}>
        <RowText label={label} sub={sub} />
      </label>
      <Switch id={id} checked={checked} disabled={disabled || locked} onChange={onChange} />
    </li>
  )
}

/** A white card with a hairline border (the app's 8px corners). */
export function Card({
  title,
  icon: Icon,
  aside,
  children,
  className,
}: {
  title?: ReactNode
  icon?: LucideIcon
  aside?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={cn('rounded-app border border-border bg-canvas p-4', className)}>
      {(title || aside) && (
        <header className="mb-3 flex items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-base font-semibold text-fg">
            {Icon && <Icon aria-hidden="true" size={20} strokeWidth={ICON.stroke} />}
            {title}
          </h2>
          {aside}
        </header>
      )}
      {children}
    </section>
  )
}

/** Shimmering placeholder lines while something loads. */
export function Skeleton({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div role="status" aria-label="Loading" className={cn('flex animate-pulse flex-col gap-2.5', className)}>
      {Array.from({ length: lines }, (_, index) => (
        <span key={index} className={cn('block h-4 rounded bg-control', index === lines - 1 ? 'w-2/3' : 'w-full')} />
      ))}
    </div>
  )
}

/** Nothing here yet, and what to do about it. */
export function EmptyNote({ icon: Icon, title, children, action }: { icon: LucideIcon; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-app border border-dashed border-border px-6 py-8 text-center">
      <Icon aria-hidden="true" className="size-8 text-fg-muted" strokeWidth={1.5} />
      <p className="font-semibold text-fg">{title}</p>
      {children && <p className="max-w-[380px] text-sm text-fg-muted">{children}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

/** A load that failed, with a way to try again. */
export function LoadError({ title, onRetry }: { title: string; onRetry: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-start gap-2 rounded-app border border-border p-4">
      <p className="font-semibold text-fg">{title}</p>
      <AppButton variant="secondary" onClick={onRetry}>
        Try again
      </AppButton>
    </div>
  )
}

/** Sends a new email confirmation link, then says so. */
export function ResendVerification({ sentClassName }: { sentClassName?: string }) {
  const toast = useToast()
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)
  async function resend() {
    setSending(true)
    try {
      await api.resendVerification()
      setSent(true)
    } catch {
      toast.show({
        tone: 'error',
        title: 'We could not send a new link',
        message: 'Please try again later.',
      })
    } finally {
      setSending(false)
    }
  }
  return sent ? (
    <p role="status" className={cn('text-sm font-semibold', sentClassName)}>
      A new link is on its way.
    </p>
  ) : (
    <AppButton variant="secondary" onClick={() => void resend()} disabled={sending}>
      {sending ? 'Sending' : 'Send a new link'}
    </AppButton>
  )
}

/** Confirm your email: needed to RSVP, join and pay online. */
export function VerifyEmailBanner() {
  return (
    <div className="flex flex-col gap-3 rounded-app bg-tint p-4 sm:flex-row sm:items-center">
      <MailWarning aria-hidden="true" className="size-6 shrink-0 text-tint-fg" />
      <p className="flex-1 text-sm text-tint-fg">Confirm your email to RSVP and join. Check your inbox for our link.</p>
      <ResendVerification sentClassName="text-tint-fg" />
    </div>
  )
}

export type ChipTone = 'ok' | 'wait' | 'off'

const CHIP_TONES: Record<ChipTone, string> = {
  ok: 'bg-tint text-tint-fg',
  wait: 'bg-wait text-wait-fg',
  off: 'bg-control text-fg',
}

/** A small status label: Active, Going, On the waitlist, Ended. */
export function StatusChip({ tone, children }: { tone: ChipTone; children: ReactNode }) {
  return <span className={cn('inline-flex h-6 shrink-0 items-center rounded-full px-2.5 text-xs font-semibold', CHIP_TONES[tone])}>{children}</span>
}

/**
 * In place of a feed setting for someone without the feed: what it is for, and the next
 * step (join the feed, or a plan that includes it). Paused accounts are told why.
 */
export function FeedOnlyNote({ icon, title, children }: { icon: LucideIcon; title: string; children: ReactNode }) {
  const auth = useAuth()
  const app = auth.user?.member_app ?? null
  return (
    <EmptyNote
      icon={icon}
      title={title}
      action={
        app === 'paused' || app === 'verify' ? undefined : (
          <Link to={app === 'join' ? '/members/join-feed' : '/membership'} className={appButtonClasses(app === 'join' ? 'primary' : 'secondary')}>
            {app === 'join' ? 'Join the member feed' : 'See plans with the feed'}
          </Link>
        )
      }
    >
      {app === 'paused'
        ? 'Your feed access is paused. These come back when it reopens.'
        : app === 'verify'
          ? 'These come with the member feed, which opens after your ID check at your next visit.'
          : children}
    </EmptyNote>
  )
}

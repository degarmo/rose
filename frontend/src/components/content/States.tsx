import { CircleAlert, RotateCw } from 'lucide-react'
import { cn } from '@/lib/cn'
import { Button } from '../ui'

export function LoadingState({ label = 'Loading', className }: { label?: string; className?: string }) {
  return (
    <div role="status" className={cn('flex items-center gap-3 py-10 text-sm text-fg-muted', className)}>
      <span aria-hidden="true" className="relative flex size-2">
                <span className="relative inline-flex size-2 rounded-full bg-primary" />
      </span>
      {label}
    </div>
  )
}

export function SkeletonCards({ count = 3 }: { count?: number }) {
  return (
    <div aria-hidden="true" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 lg:gap-6">
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className="h-56 animate-pulse rounded-card border border-border bg-surface" />
      ))}
    </div>
  )
}

interface ErrorStateProps {
  title?: string
  message?: string
  onRetry?: () => void
  className?: string
}

export function ErrorState({
  title = 'This section did not load',
  message = 'Please check your connection and try again.',
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn('flex flex-col items-start gap-4 rounded-card border border-border bg-canvas p-6 sm:flex-row sm:items-center', className)}
    >
      <CircleAlert aria-hidden="true" className="size-6 shrink-0 text-danger" />
      <div className="flex-1">
        <p className="font-semibold text-fg">{title}</p>
        <p className="mt-1 text-sm text-fg-muted">{message}</p>
      </div>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          <RotateCw aria-hidden="true" className="size-4" />
          Try again
        </Button>
      )}
    </div>
  )
}

export function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="rounded-card border border-border p-8 text-center lg:p-10">
      <p className="font-display text-card-title text-fg">{title}</p>
      <p className="mt-2 text-fg-muted">{message}</p>
    </div>
  )
}

/**
 * Placeholder for a page hero while it loads: roughly the size of a badge row,
 * a two-line heading and a summary, so nothing jumps when the content arrives.
 */
export function HeroLoading({ label }: { label: string }) {
  return (
    <div role="status">
      <span className="sr-only">{label}</span>
      <div aria-hidden="true" className="animate-pulse">
        <div className="h-6 w-24 rounded-full bg-surface" />
        <div className="mt-4 h-[1.05em] w-4/5 rounded-lg bg-surface text-[2.25rem] lg:text-h1" />
        <div className="mt-6 h-[1.6em] w-full max-w-2xl rounded bg-surface text-lead" />
        <div className="mt-1 h-[1.6em] w-2/3 max-w-xl rounded bg-surface text-lead" />
      </div>
    </div>
  )
}

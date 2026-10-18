import { CircleAlert, RotateCw } from 'lucide-react'
import { cn } from '@/lib/cn'
import { Button } from '../ui'

export function LoadingState({ label = 'Loading', className }: { label?: string; className?: string }) {
  return (
    <div role="status" className={cn('flex items-center gap-3 py-10 text-sm text-fg-muted', className)}>
      <span aria-hidden="true" className="relative flex size-2">
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-highlight/60" />
        <span className="relative inline-flex size-2 rounded-full bg-highlight" />
      </span>
      {label}
    </div>
  )
}

export function SkeletonCards({ count = 3 }: { count?: number }) {
  return (
    <div aria-hidden="true" className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className="h-80 animate-pulse rounded-2xl border border-border bg-surface" />
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
      className={cn('flex flex-col items-start gap-4 rounded-2xl border border-border bg-surface p-6 sm:flex-row sm:items-center', className)}
    >
      <CircleAlert aria-hidden="true" className="size-6 shrink-0 text-danger" />
      <div className="flex-1">
        <p className="font-semibold text-fg">{title}</p>
        <p className="mt-1 text-sm text-fg-muted">{message}</p>
      </div>
      {onRetry && (
        <Button variant="ghost" onClick={onRetry}>
          <RotateCw aria-hidden="true" className="size-4" />
          Try again
        </Button>
      )}
    </div>
  )
}

export function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-border-strong p-10 text-center">
      <p className="font-display text-2xl text-fg">{title}</p>
      <p className="mt-2 text-fg-muted">{message}</p>
    </div>
  )
}

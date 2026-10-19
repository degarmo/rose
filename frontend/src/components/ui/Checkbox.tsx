import { CircleAlert } from 'lucide-react'
import { useId, type InputHTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/lib/cn'

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: ReactNode
  hint?: string
  error?: string
}

/** A native checkbox with its label, an optional hint and an error, wired for screen readers. */
export function Checkbox({ label, hint, error, className, required, ...rest }: CheckboxProps) {
  const id = useId()
  const hintId = hint ? `${id}-hint` : undefined
  const errorId = error ? `${id}-error` : undefined
  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <div className="flex items-start gap-3">
        <input
          id={id}
          type="checkbox"
          aria-invalid={error ? true : undefined}
          aria-describedby={[hintId, errorId].filter(Boolean).join(' ') || undefined}
          aria-required={required || undefined}
          className="mt-1 size-5 shrink-0 accent-[var(--color-primary)]"
          {...rest}
        />
        <label htmlFor={id} className="text-sm leading-relaxed text-fg">
          {label}
        </label>
      </div>
      {hint && (
        <p id={hintId} className="pl-8 text-sm text-fg-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="flex items-center gap-2 pl-8 text-sm text-danger">
          <CircleAlert aria-hidden="true" className="size-4 shrink-0" />
          {error}
        </p>
      )}
    </div>
  )
}

import { Check } from 'lucide-react'
import { useId, type InputHTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/lib/cn'

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: ReactNode
  hint?: string
  error?: string
}

/**
 * The box alone: 22px, 6px corners, a 1.5px border, rose with a white check when ticked.
 * `required` tone draws the empty box in rose, as the member app's consent box does.
 */
export function CheckboxBox({ className, tone = 'default', ...rest }: Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & { tone?: 'default' | 'required' }) {
  return (
    <span className={cn('relative inline-flex size-[22px] shrink-0', className)}>
      <input
        type="checkbox"
        className={cn(
          'peer size-full cursor-pointer appearance-none rounded-[6px] border-[1.5px] bg-canvas transition-colors checked:border-primary checked:bg-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-link disabled:cursor-not-allowed disabled:border-border disabled:bg-surface',
          tone === 'required' ? 'border-primary' : 'border-fg',
        )}
        {...rest}
      />
      <Check aria-hidden="true" strokeWidth={3} className="pointer-events-none absolute inset-0 m-auto hidden size-3.5 text-white peer-checked:block" />
    </span>
  )
}

/** A checkbox with its label, an optional hint and an error, wired for screen readers. */
export function Checkbox({ label, hint, error, className, required, ...rest }: CheckboxProps) {
  const id = useId()
  const hintId = hint ? `${id}-hint` : undefined
  const errorId = error ? `${id}-error` : undefined
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <div className="flex items-start gap-3">
        <CheckboxBox
          id={id}
          aria-invalid={error ? true : undefined}
          aria-describedby={[hintId, errorId].filter(Boolean).join(' ') || undefined}
          aria-required={required || undefined}
          className="mt-0.5"
          {...rest}
        />
        <label htmlFor={id} className="text-[0.9375rem] text-fg">
          {label}
        </label>
      </div>
      {hint && (
        <p id={hintId} className="pl-[34px] text-[0.8125rem] text-fg-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="pl-[34px] text-[0.8125rem] text-danger">
          {error}
        </p>
      )}
    </div>
  )
}

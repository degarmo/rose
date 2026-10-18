import { CircleAlert } from 'lucide-react'
import { useId, type ReactNode } from 'react'

export interface FieldControlProps {
  id: string
  invalid: boolean
  'aria-describedby'?: string
  'aria-required'?: boolean
}

interface FormFieldProps {
  label: string
  hint?: string
  error?: string
  required?: boolean
  optionalLabel?: string
  children: (control: FieldControlProps) => ReactNode
}

/** Wires a label, hint and error message to a single control via a render prop. */
export function FormField({ label, hint, error, required, optionalLabel = 'Optional', children }: FormFieldProps) {
  const id = useId()
  const hintId = hint ? `${id}-hint` : undefined
  const errorId = error ? `${id}-error` : undefined
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="flex items-baseline justify-between gap-4 text-sm font-medium text-fg">
        {label}
        {!required && optionalLabel && <span className="text-xs font-normal text-fg-subtle">{optionalLabel}</span>}
      </label>
      {hint && (
        <p id={hintId} className="text-sm text-fg-muted">
          {hint}
        </p>
      )}
      {children({ id, invalid: Boolean(error), 'aria-describedby': describedBy, 'aria-required': required })}
      {error && (
        <p id={errorId} className="flex items-center gap-2 text-sm text-danger">
          <CircleAlert aria-hidden="true" className="size-4 shrink-0" />
          {error}
        </p>
      )}
    </div>
  )
}

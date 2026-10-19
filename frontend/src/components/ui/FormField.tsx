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

/** Wires a label (14/600), hint and error message (13px) to a single control via a render prop. */
export function FormField({ label, hint, error, required, optionalLabel = 'Optional', children }: FormFieldProps) {
  const id = useId()
  const hintId = hint ? `${id}-hint` : undefined
  const errorId = error ? `${id}-error` : undefined
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className="flex flex-col gap-1.5 text-sm">
      <label htmlFor={id} className="flex items-baseline justify-between gap-4 font-semibold text-fg">
        {label}
        {!required && optionalLabel && <span className="text-[0.8125rem] font-normal text-fg-muted">{optionalLabel}</span>}
      </label>
      {children({ id, invalid: Boolean(error), 'aria-describedby': describedBy, 'aria-required': required })}
      {hint && (
        <p id={hintId} className="text-[0.8125rem] text-fg-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-[0.8125rem] text-danger">
          {error}
        </p>
      )}
    </div>
  )
}

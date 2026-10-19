import { useId } from 'react'
import { cn } from '@/lib/cn'

interface ToggleProps {
  label: string
  hint?: string
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
}

/** A labelled on/off switch built on a native checkbox. */
export function Toggle({ label, hint, checked, onChange, disabled }: ToggleProps) {
  const id = useId()
  return (
    <div className="flex items-start justify-between gap-4">
      <label htmlFor={id} className="flex-1 cursor-pointer">
        <span className="block text-sm font-medium text-fg">{label}</span>
        {hint && <span className="mt-0.5 block text-sm text-fg-muted">{hint}</span>}
      </label>
      <span className="relative inline-flex h-7 w-12 shrink-0">
        <input
          id={id}
          type="checkbox"
          role="switch"
          checked={checked}
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked)}
          className="peer absolute inset-0 z-10 size-full cursor-pointer opacity-0"
        />
        <span
          aria-hidden="true"
          className={cn(
            'absolute inset-0 rounded-full border transition-colors duration-300 peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-highlight',
            checked ? 'border-primary bg-primary' : 'border-border-strong bg-surface-sunken',
          )}
        />
        <span
          aria-hidden="true"
          className={cn('absolute top-1 size-5 rounded-full bg-knob shadow-sm transition-transform duration-300', checked ? 'translate-x-6' : 'translate-x-1')}
        />
      </span>
    </div>
  )
}

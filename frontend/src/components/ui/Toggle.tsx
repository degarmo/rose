import { useId, type ReactNode } from 'react'
import { cn } from '@/lib/cn'

/** The switch alone: 40×22, an 18px knob; grey off, rose on. Built on a native checkbox. */
export function Switch({
  id,
  checked,
  onChange,
  disabled,
  label,
  className,
}: {
  id?: string
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
  /** An accessible name when there is no visible label. */
  label?: string
  className?: string
}) {
  return (
    <span className={cn('relative inline-flex h-[22px] w-10 shrink-0', className)}>
      <input
        id={id}
        type="checkbox"
        role="switch"
        aria-label={label}
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="peer absolute inset-0 z-10 size-full cursor-pointer opacity-0 disabled:cursor-not-allowed"
      />
      <span
        aria-hidden="true"
        className="absolute inset-0 rounded-[11px] bg-border transition-colors duration-150 peer-checked:bg-primary peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-link peer-disabled:opacity-50"
      />
      <span
        aria-hidden="true"
        className="absolute left-0.5 top-0.5 size-[18px] rounded-full bg-white shadow-[0_1px_2px_rgb(0_0_0/0.15)] transition-transform duration-150 peer-checked:translate-x-[18px]"
      />
    </span>
  )
}

interface ToggleProps {
  label: string
  hint?: ReactNode
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
  className?: string
}

/** A labelled switch: the label (600) and an optional muted hint, the switch on the right. */
export function Toggle({ label, hint, checked, onChange, disabled, className }: ToggleProps) {
  const id = useId()
  return (
    <div className={cn('flex items-center justify-between gap-4', className)}>
      <label htmlFor={id} className="flex-1 cursor-pointer">
        <span className="block font-semibold text-fg">{label}</span>
        {hint && <span className="block text-meta text-fg-muted">{hint}</span>}
      </label>
      <Switch id={id} checked={checked} onChange={onChange} disabled={disabled} />
    </div>
  )
}

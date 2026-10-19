import { cn } from '@/lib/cn'

export interface SegmentOption<T extends string> {
  value: T
  label: string
}

/**
 * The website's segmented tabs (design system: "Site tabs"): a bordered pill holding
 * 34px items, the chosen one filled with the text colour.
 */
export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
  className,
}: {
  label: string
  options: SegmentOption<T>[]
  value: T
  onChange: (value: T) => void
  className?: string
}) {
  return (
    <div role="group" aria-label={label} className={cn('inline-flex rounded-full border border-border p-[3px] text-[0.8125rem] font-semibold sm:text-sm', className)}>
      {options.map((option) => {
        const active = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.value)}
            className={cn(
              'inline-flex h-[30px] items-center rounded-full px-3.5 transition-colors duration-150 sm:h-[34px] sm:px-[18px]',
              active ? 'bg-fg text-canvas' : 'text-fg-muted hover:text-fg',
            )}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}

/**
 * Filter chips (design system: "Filters"): 34px pills, the chosen one filled with the text
 * colour. A row scrolls sideways on phones rather than wrapping.
 */
export function FilterChips<T extends string>({
  label,
  options,
  value,
  onChange,
  className,
}: {
  label: string
  options: SegmentOption<T>[]
  value: T
  onChange: (value: T) => void
  className?: string
}) {
  return (
    <div role="group" aria-label={label} className={cn('flex gap-2 overflow-x-auto text-xs font-semibold [scrollbar-width:none] sm:text-[0.8125rem]', className)}>
      {options.map((option) => {
        const active = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.value)}
            className={cn(
              'inline-flex h-8 shrink-0 items-center whitespace-nowrap rounded-full border px-3.5 transition-colors duration-150 sm:h-[34px] sm:px-4',
              active ? 'border-fg bg-fg text-canvas' : 'border-border bg-canvas text-fg hover:border-fg-muted',
            )}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}

import { cn } from '@/lib/cn'

/**
 * Website fields (design system: "Inputs"): 48px, 1px border, 12px corners. Focus and
 * errors thicken the border to 1.5px, drawn with an inset shadow so nothing shifts.
 */
export function fieldClasses(invalid: boolean | undefined, className?: string) {
  return cn(
    'block w-full rounded-field border bg-canvas px-4 text-[0.9375rem] text-fg placeholder:text-fg-muted',
    'transition-[border-color,box-shadow] duration-150 ease-out focus:outline-none',
    invalid
      ? 'border-danger shadow-[inset_0_0_0_0.5px_var(--color-danger)]'
      : 'border-border hover:border-fg-muted focus:border-fg focus:shadow-[inset_0_0_0_0.5px_var(--color-fg)]',
    'disabled:cursor-not-allowed disabled:bg-surface disabled:text-fg-muted',
    className,
  )
}

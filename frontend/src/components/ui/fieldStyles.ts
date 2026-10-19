import { cn } from '@/lib/cn'

export function fieldClasses(invalid: boolean | undefined, className?: string) {
  return cn(
    'block w-full rounded-field border bg-surface-sunken px-4 py-3 text-base text-fg placeholder:text-fg-subtle',
    'transition-colors duration-300 ease-velvet focus:outline-none focus-visible:outline-2 focus-visible:outline-offset-2',
    invalid
      ? 'border-error-mark focus-visible:outline-error-mark'
      : 'border-border-strong hover:border-fg-muted focus-visible:outline-highlight',
    'disabled:cursor-not-allowed disabled:opacity-60',
    className,
  )
}

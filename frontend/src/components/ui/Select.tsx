import { ChevronDown } from 'lucide-react'
import type { SelectHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'
import { fieldClasses } from './fieldStyles'

export interface SelectOption {
  value: string
  label: string
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  options: SelectOption[]
  invalid?: boolean
}

export function Select({ options, invalid, className, ...rest }: SelectProps) {
  return (
    <div className="relative">
      <select aria-invalid={invalid || undefined} className={fieldClasses(invalid, cn('h-12 appearance-none pr-11', className))} {...rest}>
        {options.map((option) => (
          <option key={option.value} value={option.value} className="bg-canvas text-fg">
            {option.label}
          </option>
        ))}
      </select>
      <ChevronDown aria-hidden="true" strokeWidth={2} className="pointer-events-none absolute right-4 top-1/2 size-3.5 -translate-y-1/2 text-fg" />
    </div>
  )
}

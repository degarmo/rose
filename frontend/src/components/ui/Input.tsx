import type { InputHTMLAttributes } from 'react'
import { fieldClasses } from './fieldStyles'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean
}

export function Input({ invalid, className, ...rest }: InputProps) {
  return <input aria-invalid={invalid || undefined} className={fieldClasses(invalid, className)} {...rest} />
}

import type { TextareaHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'
import { fieldClasses } from './fieldStyles'

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean
}

export function Textarea({ invalid, className, rows = 5, ...rest }: TextareaProps) {
  return <textarea rows={rows} aria-invalid={invalid || undefined} className={fieldClasses(invalid, cn('min-h-[140px] resize-y py-3', className))} {...rest} />
}

import type { TextareaHTMLAttributes } from 'react'
import { fieldClasses } from './fieldStyles'

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean
}

export function Textarea({ invalid, className, rows = 6, ...rest }: TextareaProps) {
  return (
    <textarea
      rows={rows}
      aria-invalid={invalid || undefined}
      className={fieldClasses(invalid, `min-h-36 resize-y leading-relaxed ${className ?? ''}`)}
      {...rest}
    />
  )
}

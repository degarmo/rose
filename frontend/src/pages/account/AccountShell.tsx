import type { ReactNode } from 'react'
import { GUTTER } from '@/components/ui'
import { cn } from '@/lib/cn'

interface AccountShellProps {
  title: string
  lede?: ReactNode
  children: ReactNode
  footer?: ReactNode
}

/**
 * Every sign-in style page (no design: laid out like Contact): the title and lead on the
 * left, a narrow form or confirmation on the right; stacked on phones.
 */
export function AccountShell({ title, lede, children, footer }: AccountShellProps) {
  return (
    <div className={cn('mx-auto grid max-w-[1440px] gap-6 pb-16 pt-7 lg:grid-cols-2 lg:gap-24 lg:pb-24 lg:pt-16', GUTTER)}>
      <div className="flex flex-col gap-3 lg:gap-4">
        <h1 className="text-[2.25rem] font-light leading-[1.05] text-fg lg:text-h1">{title}</h1>
        {lede && <div className="max-w-[440px] text-fg-muted lg:text-lead">{lede}</div>}
      </div>
      <div className="w-full lg:max-w-[440px]">
        {children}
        {footer && <div className="mt-6 text-sm text-fg-muted">{footer}</div>}
      </div>
    </div>
  )
}

/** A form-wide problem above the fields: the 1.5px danger border of an invalid field. */
export const FORM_ALERT = 'rounded-field border-[1.5px] border-danger p-3 text-[0.8125rem] text-danger'

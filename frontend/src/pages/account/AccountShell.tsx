import type { ReactNode } from 'react'
import { Card } from '@/components/ui'

interface AccountShellProps {
  title: string
  lede?: ReactNode
  children: ReactNode
  footer?: ReactNode
}

/** A quiet, centred card for every sign-in style page. */
export function AccountShell({ title, lede, children, footer }: AccountShellProps) {
  return (
    <div className="texture-shadow relative flex min-h-svh items-start justify-center px-5 pb-20 pt-32 sm:items-center">
      <div className="w-full max-w-md">
        <Card className="p-6 sm:p-10">
          <h1 className="text-4xl text-fg">{title}</h1>
          {lede && <div className="mt-3 leading-relaxed text-fg-muted">{lede}</div>}
          <div className="mt-8">{children}</div>
        </Card>
        {footer && <div className="mt-6 text-center text-sm text-fg-muted">{footer}</div>}
      </div>
    </div>
  )
}

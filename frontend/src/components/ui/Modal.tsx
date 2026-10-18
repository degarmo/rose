import { X } from 'lucide-react'
import { useEffect, useId, useRef, type ReactNode } from 'react'
import { cn } from '@/lib/cn'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  hideTitle?: boolean
  variant?: 'dialog' | 'sheet'
  children: ReactNode
  footer?: ReactNode
}

/**
 * Built on the native <dialog>, which traps focus, restores it on close and
 * closes on Escape without extra code.
 */
export function Modal({ open, onClose, title, hideTitle = false, variant = 'dialog', children, footer }: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === ref.current) onClose()
      }}
      className={cn(
        'm-0 max-h-none max-w-none border-0 bg-transparent p-0 text-fg open:flex',
        variant === 'sheet' ? 'h-dvh w-screen' : 'h-dvh w-screen items-center justify-center p-4',
      )}
    >
      <div
        className={cn(
          'relative flex flex-col bg-surface',
          variant === 'sheet'
            ? 'h-full w-full px-6 pb-10 pt-6'
            : 'max-h-[90dvh] w-full max-w-lg overflow-y-auto rounded-2xl border border-border p-6 sm:p-8',
        )}
      >
        <div className="flex items-start justify-between gap-6">
          <h2 id={titleId} className={cn('text-2xl text-fg', hideTitle && 'sr-only')}>
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="-mr-2 -mt-1 ml-auto inline-flex size-11 items-center justify-center rounded-full text-fg-muted hover:text-fg"
          >
            <X aria-hidden="true" className="size-5" />
            <span className="sr-only">Close</span>
          </button>
        </div>
        <div className="mt-4 flex-1">{children}</div>
        {footer && <div className="mt-8 flex flex-wrap justify-end gap-3">{footer}</div>}
      </div>
    </dialog>
  )
}

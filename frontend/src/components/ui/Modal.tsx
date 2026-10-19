import { X } from 'lucide-react'
import { useEffect, useId, useRef, type ReactNode } from 'react'
import { cn } from '@/lib/cn'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  hideTitle?: boolean
  variant?: 'dialog' | 'sheet'
  size?: 'md' | 'wide'
  children: ReactNode
  footer?: ReactNode
}

/**
 * Built on the native <dialog>, which traps focus, restores it on close and closes on
 * Escape without extra code. A white panel with 20px corners and the modal shadow.
 */
export function Modal({ open, onClose, title, hideTitle = false, variant = 'dialog', size = 'md', children, footer }: ModalProps) {
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
          'relative flex flex-col bg-canvas',
          variant === 'sheet'
            ? 'h-full w-full overflow-y-auto px-5 pb-10 pt-5'
            : cn('max-h-[92dvh] w-full overflow-y-auto rounded-panel p-6 shadow-modal sm:p-8', size === 'wide' ? 'max-w-5xl' : 'max-w-lg'),
        )}
      >
        <div className="flex items-start justify-between gap-6">
          <h2 id={titleId} className={cn('text-2xl text-fg', hideTitle && 'sr-only')}>
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="-mr-2 -mt-1 ml-auto inline-flex size-10 items-center justify-center rounded-full text-fg-muted hover:text-fg"
          >
            <X aria-hidden="true" className="size-5" />
            <span className="sr-only">Close</span>
          </button>
        </div>
        <div className="mt-4 min-h-0 flex-1">{children}</div>
        {footer && <div className="mt-8 flex flex-wrap justify-end gap-3">{footer}</div>}
      </div>
    </dialog>
  )
}

import { useEffect, useId, useRef } from 'react'
import { cn } from '@/lib/cn'

export interface SheetAction {
  label: string
  onSelect: () => void
  danger?: boolean
}

/**
 * A centred sheet of full-width stacked rows with Cancel last, on the native <dialog>
 * (focus is trapped and restored, Escape closes).
 */
export function ActionSheet({ open, onClose, actions, label }: { open: boolean; onClose: () => void; actions: SheetAction[]; label: string }) {
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
      className="m-0 h-dvh max-h-none w-screen max-w-none items-center justify-center bg-transparent p-4 open:flex"
    >
      <div className="w-full max-w-[400px] overflow-hidden rounded-xl bg-surface-raised text-fg shadow-[var(--ui-shadow)]">
        <h2 id={titleId} className="sr-only">
          {label}
        </h2>
        <ul className="divide-y divide-border">
          {actions.map((action) => (
            <li key={action.label}>
              <button
                type="button"
                onClick={() => {
                  onClose()
                  action.onSelect()
                }}
                className={cn(
                  'flex min-h-12 w-full items-center justify-center px-4 text-sm hover:bg-surface',
                  action.danger ? 'font-semibold text-danger' : 'text-fg',
                )}
              >
                {action.label}
              </button>
            </li>
          ))}
          <li>
            <button type="button" onClick={onClose} className="flex min-h-12 w-full items-center justify-center px-4 text-sm text-fg hover:bg-surface">
              Cancel
            </button>
          </li>
        </ul>
      </div>
    </dialog>
  )
}

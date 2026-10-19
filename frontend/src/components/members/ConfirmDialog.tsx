import type { ReactNode } from 'react'
import { Button, Modal } from '../ui'

interface ConfirmDialogProps {
  open: boolean
  title: string
  children: ReactNode
  confirmLabel: string
  busy?: boolean
  disabled?: boolean
  onConfirm: () => void
  onClose: () => void
}

export function ConfirmDialog({ open, title, children, confirmLabel, busy = false, disabled = false, onConfirm, onClose }: ConfirmDialogProps) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={onConfirm} disabled={busy || disabled} aria-busy={busy}>
            {busy ? 'Working' : confirmLabel}
          </Button>
        </>
      }
    >
      <div className="space-y-3 leading-relaxed text-fg-muted">{children}</div>
    </Modal>
  )
}

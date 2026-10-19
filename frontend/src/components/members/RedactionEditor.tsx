import { Crop, Eraser, Grid3x3, RotateCw, Square, Undo2 } from 'lucide-react'
import { useEffect, useRef, useState, type PointerEvent } from 'react'
import { cn } from '@/lib/cn'
import { rectFromPoints, renderRedacted, type Edits, type Rect, type RedactMode, type Source } from '@/lib/redact'

interface RedactionEditorProps {
  source: Source & CanvasImageSource
  edits: Edits
  onChange: (edits: Edits) => void
}

const MIN_SIZE = 0.02

function ToolButton({ active, onClick, label, children }: { active?: boolean; onClick: () => void; label: string; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        'inline-flex h-8 items-center gap-1.5 rounded-lg border px-3 text-sm font-semibold transition-colors',
        active ? 'border-primary bg-primary text-on-primary' : 'border-border-strong text-fg hover:border-highlight',
      )}
    >
      {children}
      <span>{label}</span>
    </button>
  )
}

/**
 * Draw rectangles to cover or pixelate, rotate, and crop. Everything renders
 * on a canvas on this device; only the rendered result is ever uploaded.
 */
export function RedactionEditor({ source, edits, onChange }: RedactionEditorProps) {
  const [mode, setMode] = useState<RedactMode>('fill')
  const [cropping, setCropping] = useState(false)
  const [draft, setDraft] = useState<Rect | null>(null)
  const start = useRef<{ x: number; y: number } | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    // While cropping, show the whole rotated image so the crop can be redrawn.
    const preview = renderRedacted(source, cropping ? { ...edits, crop: null, redactions: [] } : edits)
    canvas.width = preview.width
    canvas.height = preview.height
    canvas.getContext('2d')?.drawImage(preview as unknown as CanvasImageSource, 0, 0)
  }, [source, edits, cropping])

  function point(event: PointerEvent<HTMLDivElement>) {
    const box = event.currentTarget.getBoundingClientRect()
    return { x: (event.clientX - box.left) / box.width, y: (event.clientY - box.top) / box.height }
  }

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    event.currentTarget.setPointerCapture?.(event.pointerId)
    start.current = point(event)
    setDraft(null)
  }

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!start.current) return
    const now = point(event)
    setDraft(rectFromPoints(start.current.x, start.current.y, now.x, now.y))
  }

  function onPointerUp() {
    const rect = draft
    start.current = null
    setDraft(null)
    if (!rect || rect.w < MIN_SIZE || rect.h < MIN_SIZE) return
    if (cropping) {
      // A new crop changes the frame, so earlier cover-ups would land in the wrong place.
      onChange({ ...edits, crop: rect, redactions: [] })
      setCropping(false)
    } else {
      onChange({ ...edits, redactions: [...edits.redactions, { ...rect, mode }] })
    }
  }

  const rotation = ((edits.rotation + 90) % 360) as Edits['rotation']
  const sideways = edits.rotation === 90 || edits.rotation === 270
  const shown = cropping || !edits.crop ? { w: 1, h: 1 } : edits.crop
  const aspect = ((sideways ? source.height : source.width) * shown.w) / ((sideways ? source.width : source.height) * shown.h)

  return (
    <div>
      <div className="flex flex-wrap gap-2" role="toolbar" aria-label="Redaction tools">
        <ToolButton active={!cropping && mode === 'fill'} onClick={() => { setCropping(false); setMode('fill') }} label="Cover">
          <Square aria-hidden="true" className="size-4" />
        </ToolButton>
        <ToolButton active={!cropping && mode === 'pixelate'} onClick={() => { setCropping(false); setMode('pixelate') }} label="Pixelate">
          <Grid3x3 aria-hidden="true" className="size-4" />
        </ToolButton>
        <ToolButton active={cropping} onClick={() => setCropping((value) => !value)} label="Crop">
          <Crop aria-hidden="true" className="size-4" />
        </ToolButton>
        <ToolButton onClick={() => onChange({ rotation, crop: null, redactions: [] })} label="Rotate">
          <RotateCw aria-hidden="true" className="size-4" />
        </ToolButton>
        <ToolButton onClick={() => onChange({ ...edits, redactions: edits.redactions.slice(0, -1) })} label="Undo">
          <Undo2 aria-hidden="true" className="size-4" />
        </ToolButton>
        <ToolButton onClick={() => onChange({ ...edits, crop: null, redactions: [] })} label="Reset">
          <Eraser aria-hidden="true" className="size-4" />
        </ToolButton>
      </div>
      <p className="mt-3 text-sm text-fg-muted" aria-live="polite">
        {cropping
          ? 'Drag to choose the part of the photo to keep.'
          : `Drag over faces, tattoos, signs or anything identifying to ${mode === 'fill' ? 'cover it completely' : 'pixelate it'}. Covering is the safest choice.`}
      </p>
      <div
        className="relative mx-auto mt-4 select-none overflow-hidden rounded-xl bg-surface-sunken"
        style={{ maxWidth: `min(100%, calc(60dvh * ${aspect.toFixed(4)}))` }}
      >
        <canvas ref={canvasRef} className="block h-auto w-full" aria-label="Photo being edited" role="img" />
        <div
          className="absolute inset-0 cursor-crosshair touch-none"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={() => { start.current = null; setDraft(null) }}
          data-testid="redaction-surface"
        >
          {draft && (
            <div
              className={cn('absolute border-2', cropping ? 'border-highlight bg-highlight/10' : mode === 'fill' ? 'border-fg bg-ink-950/80' : 'border-fg bg-fg/20')}
              style={{ left: `${draft.x * 100}%`, top: `${draft.y * 100}%`, width: `${draft.w * 100}%`, height: `${draft.h * 100}%` }}
            />
          )}
        </div>
      </div>
      <p className="mt-2 text-xs text-fg-subtle">
        {edits.redactions.length} area{edits.redactions.length === 1 ? '' : 's'} covered{edits.crop ? ', cropped' : ''}
        {edits.rotation ? `, rotated ${edits.rotation}°` : ''}. The original photo never leaves your device.
      </p>
    </div>
  )
}

import { Crop, Droplet, RotateCw, Square } from 'lucide-react'
import { useEffect, useRef, useState, type CSSProperties, type PointerEvent, type ReactNode } from 'react'
import { cn } from '@/lib/cn'
import { clampRect, rectFromPoints, renderRedacted, type Edits, type Rect, type RedactMode, type Source } from '@/lib/redact'

interface RedactionEditorProps {
  source: Source & CanvasImageSource
  edits: Edits
  onChange: (edits: Edits) => void
  /**
   * `overlay`: the tools float over the bottom of the photo, which fills the parent's
   * height (design: Create on wider screens). `stacked`: the photo, then a row of 44px
   * tools under it (design: Create on phones; also the profile picture).
   */
  layout?: 'overlay' | 'stacked'
  /** The photo area's size in the stacked layout. */
  stageClassName?: string
  /** 16px side padding around the tools and hint (a full-width photo above them). */
  inset?: boolean
  /** Extra controls drawn over the photo, such as the arrows between photos. */
  children?: ReactNode
}

const MIN_SIZE = 0.02
const RATIOS = [
  { label: '1:1', value: 1 },
  { label: '4:5', value: 4 / 5 },
] as const

/** A crop of the given shape, as large as fits and centred, in fractions of the rotated photo. */
function centredCrop(width: number, height: number, ratio: number): Rect {
  if (width / height > ratio) {
    const w = (height * ratio) / width
    return { x: (1 - w) / 2, y: 0, w, h: 1 }
  }
  const h = width / ratio / height
  return { x: 0, y: (1 - h) / 2, w: 1, h }
}

function sameRect(a: Rect | null, b: Rect) {
  return Boolean(a) && Math.abs(a!.x - b.x) < 0.001 && Math.abs(a!.y - b.y) < 0.001 && Math.abs(a!.w - b.w) < 0.001 && Math.abs(a!.h - b.h) < 0.001
}

/**
 * Moves the cover-ups into a new crop's frame, so changing the crop never uncovers
 * anything; parts that fall outside the new crop are cut away with the rest of the photo.
 */
function recrop(edits: Edits, crop: Rect | null): Edits {
  const from = edits.crop ?? { x: 0, y: 0, w: 1, h: 1 }
  const to = crop ?? { x: 0, y: 0, w: 1, h: 1 }
  const redactions = edits.redactions.flatMap((area) => {
    const left = (from.x + area.x * from.w - to.x) / to.w
    const top = (from.y + area.y * from.h - to.y) / to.h
    const right = left + (area.w * from.w) / to.w
    const bottom = top + (area.h * from.h) / to.h
    const x = Math.max(0, left)
    const y = Math.max(0, top)
    const w = Math.min(1, right) - x
    const h = Math.min(1, bottom) - y
    return w > 0 && h > 0 ? [{ ...clampRect({ x, y, w, h }), mode: area.mode }] : []
  })
  return { ...edits, crop, redactions }
}

function ToolButton({
  active,
  onClick,
  label,
  icon,
  big = false,
  hideLabel = false,
  className,
}: {
  active?: boolean
  onClick: () => void
  label: string
  icon?: ReactNode
  big?: boolean
  hideLabel?: boolean
  className?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        'inline-flex items-center justify-center gap-1.5 rounded-app border text-sm font-semibold transition-colors duration-150',
        big ? 'h-11 px-3' : 'h-8 px-3.5',
        active ? 'border-fg bg-fg text-canvas' : cn('border-border text-fg hover:bg-surface', big ? 'bg-canvas' : 'bg-canvas/90'),
        className,
      )}
    >
      {icon}
      <span className={cn(hideLabel && 'sr-only')}>{label}</span>
    </button>
  )
}

/**
 * Crop & redact (design: "Create · Crop & redact"): draw boxes to blur or block, crop
 * freely or to 1:1 or 4:5, rotate. Everything renders on a canvas on this device; only the
 * rendered result is ever uploaded.
 */
export function RedactionEditor({ source, edits, onChange, layout = 'stacked', stageClassName, inset = false, children }: RedactionEditorProps) {
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
      onChange(recrop(edits, rect))
      setCropping(false)
    } else {
      onChange({ ...edits, redactions: [...edits.redactions, { ...rect, mode }] })
    }
  }

  const rotation = ((edits.rotation + 90) % 360) as Edits['rotation']
  const sideways = edits.rotation === 90 || edits.rotation === 270
  const width = sideways ? source.height : source.width
  const height = sideways ? source.width : source.height
  const shown = cropping || !edits.crop ? { w: 1, h: 1 } : edits.crop
  const aspect = (width * shown.w) / (height * shown.h)
  const overlay = layout === 'overlay'

  const choose = (next: RedactMode) => {
    setCropping(false)
    setMode(next)
  }
  const tools = [
    <ToolButton key="blur" big={!overlay} className={overlay ? undefined : 'flex-1'} active={!cropping && mode === 'pixelate'} onClick={() => choose('pixelate')} label="Blur" icon={<Droplet aria-hidden="true" className="size-4" strokeWidth={1.8} />} />,
    <ToolButton key="block" big={!overlay} className={overlay ? undefined : 'flex-1'} active={!cropping && mode === 'fill'} onClick={() => choose('fill')} label="Block" icon={<Square aria-hidden="true" className="size-4" strokeWidth={1.8} />} />,
    <ToolButton key="crop" big={!overlay} className={overlay ? undefined : 'flex-1'} active={cropping} onClick={() => setCropping((value) => !value)} label="Crop" icon={<Crop aria-hidden="true" className="size-4" strokeWidth={1.8} />} />,
    <ToolButton
      key="undo"
      big={!overlay}
      className={overlay ? undefined : 'w-[72px]'}
      onClick={() => onChange({ ...edits, redactions: edits.redactions.slice(0, -1) })}
      label="Undo"
    />,
  ]

  // The frame matches the photo's shape and fits inside the stage, so pointer positions map straight onto it.
  const frame: CSSProperties = { width: `min(100cqw, calc(100cqh * ${aspect.toFixed(4)}))`, aspectRatio: aspect.toFixed(4) }

  const stage = (
    <div className={cn('relative flex select-none items-center justify-center overflow-hidden bg-surface [container-type:size]', overlay ? 'min-h-0 flex-1' : stageClassName ?? 'aspect-[4/5] max-h-[58dvh] w-full')}>
      <div className="relative" style={frame}>
        <canvas ref={canvasRef} className="block size-full" aria-label="Photo being edited" role="img" />
        {!cropping &&
          edits.redactions.map((area, index) => (
            <span
              // Redactions are only ever appended or removed from the end.
              key={index}
              aria-hidden="true"
              className="pointer-events-none absolute outline-2 outline-offset-2 outline-primary outline-dashed"
              style={{ left: `${area.x * 100}%`, top: `${area.y * 100}%`, width: `${area.w * 100}%`, height: `${area.h * 100}%` }}
            >
              <span className="absolute -top-6 left-0 rounded-sm bg-canvas/85 px-1 text-[0.6875rem] font-semibold leading-4 text-link">{area.mode === 'fill' ? 'Block' : 'Blur'}</span>
            </span>
          ))}
        <div
          className="absolute inset-0 cursor-crosshair touch-none"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={() => {
            start.current = null
            setDraft(null)
          }}
          data-testid="redaction-surface"
        >
          {draft && (
            <div
              className={cn(
                'absolute',
                cropping ? 'border-2 border-primary bg-primary/10' : cn('outline-2 outline-offset-2 outline-primary outline-dashed', mode === 'fill' ? 'bg-[#0d0a0b]' : 'bg-white/30 backdrop-blur-md'),
              )}
              style={{ left: `${draft.x * 100}%`, top: `${draft.y * 100}%`, width: `${draft.w * 100}%`, height: `${draft.h * 100}%` }}
            />
          )}
        </div>
      </div>
      {children}
      {overlay && (
        <div role="toolbar" aria-label="Redaction tools" className="absolute bottom-4 left-4 flex gap-2">
          {tools}
        </div>
      )}
      <div role="group" aria-label="Shape and rotation" className="absolute bottom-4 right-4 flex gap-2">
        <ToolButton onClick={() => onChange({ rotation, crop: null, redactions: [] })} label="Rotate" hideLabel icon={<RotateCw aria-hidden="true" className="size-4" strokeWidth={1.8} />} className="w-8 px-0" />
        {RATIOS.map((ratio) => {
          const crop = centredCrop(width, height, ratio.value)
          const active = sameRect(edits.crop, crop)
          return (
            <ToolButton
              key={ratio.label}
              label={ratio.label}
              active={active}
              className="px-3"
              onClick={() => {
                setCropping(false)
                onChange(recrop(edits, active ? null : crop))
              }}
            />
          )
        })}
      </div>
    </div>
  )

  const count = edits.redactions.length
  return (
    <div className={cn('flex flex-col', overlay && 'h-full')}>
      {stage}
      {!overlay && (
        <div role="toolbar" aria-label="Redaction tools" className={cn('flex gap-2 pt-4', inset && 'px-4')}>
          {tools}
        </div>
      )}
      <div className={cn('text-meta text-fg-muted', overlay ? 'flex min-h-[60px] flex-col justify-center px-4 py-2' : cn('pt-3', inset && 'px-4'))}>
        <p aria-live="polite">
          {cropping ? 'Drag to choose the part of the photo to keep.' : 'Draw a box over anything that should not be shared. Blurred and blocked areas are applied before upload.'}
        </p>
        <p>
          {count} area{count === 1 ? '' : 's'} covered{edits.crop ? ', cropped' : ''}
          {edits.rotation ? `, rotated ${edits.rotation}°` : ''}. The original photo never leaves your device.{' '}
          {(count > 0 || edits.crop) && (
            <button type="button" onClick={() => onChange({ ...edits, crop: null, redactions: [] })} className="min-h-6 font-semibold text-fg hover:text-fg-muted">
              Reset
            </button>
          )}
        </p>
      </div>
    </div>
  )
}

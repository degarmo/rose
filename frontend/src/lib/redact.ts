/**
 * In-browser redaction. Everything happens on canvases on the device; the only
 * thing that is ever uploaded is the rendered result, never the original file.
 *
 * Rendering order: rotate, then crop, then cover or pixelate each rectangle.
 * Rectangles are stored as fractions (0 to 1) of the image they were drawn on.
 */

export type RedactMode = 'fill' | 'pixelate'
export type Rotation = 0 | 90 | 180 | 270

export interface Rect {
  x: number
  y: number
  w: number
  h: number
}

export interface Redaction extends Rect {
  mode: RedactMode
}

export interface Edits {
  rotation: Rotation
  /** Fraction of the rotated image to keep; null keeps all of it. */
  crop: Rect | null
  /** Fractions of the cropped image. */
  redactions: Redaction[]
}

export const NO_EDITS: Edits = { rotation: 0, crop: null, redactions: [] }

/** Longest side of an uploaded image, in pixels. */
export const MAX_OUTPUT = 2400
/** Pixelation keeps about this many blocks across a region's long side: heavy on purpose. */
export const PIXEL_BLOCKS = 10
export const FILL_COLOUR = '#0d0a0b'
export const JPEG_QUALITY = 0.9

export interface Context2D {
  fillStyle: string | CanvasGradient | CanvasPattern
  imageSmoothingEnabled: boolean
  drawImage(image: unknown, ...args: number[]): void
  fillRect(x: number, y: number, w: number, h: number): void
  translate(x: number, y: number): void
  rotate(angle: number): void
}

export interface CanvasLike {
  width: number
  height: number
  getContext(type: '2d'): Context2D | null
  toBlob(callback: (blob: Blob | null) => void, type?: string, quality?: number): void
}

export type CanvasFactory = (width: number, height: number) => CanvasLike

export interface Source {
  width: number
  height: number
}

export const browserCanvas: CanvasFactory = (width, height) => {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  return canvas as unknown as CanvasLike
}

function context(canvas: CanvasLike): Context2D {
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Canvas is not available in this browser.')
  return ctx
}

export function clampRect(rect: Rect): Rect {
  const x = Math.min(Math.max(rect.x, 0), 1)
  const y = Math.min(Math.max(rect.y, 0), 1)
  return { x, y, w: Math.min(Math.max(rect.w, 0), 1 - x), h: Math.min(Math.max(rect.h, 0), 1 - y) }
}

/** Normalise a drag from (x1, y1) to (x2, y2) into a positive rectangle. */
export function rectFromPoints(x1: number, y1: number, x2: number, y2: number): Rect {
  return clampRect({ x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1) })
}

export function rotate(source: Source, rotation: Rotation, createCanvas: CanvasFactory): CanvasLike {
  const sideways = rotation === 90 || rotation === 270
  const canvas = createCanvas(sideways ? source.height : source.width, sideways ? source.width : source.height)
  const ctx = context(canvas)
  ctx.translate(canvas.width / 2, canvas.height / 2)
  ctx.rotate((rotation * Math.PI) / 180)
  ctx.drawImage(source, -source.width / 2, -source.height / 2)
  return canvas
}

function pixelate(ctx: Context2D, canvas: CanvasLike, x: number, y: number, w: number, h: number, createCanvas: CanvasFactory) {
  const scale = PIXEL_BLOCKS / Math.max(w, h)
  const smallW = Math.max(1, Math.round(w * scale))
  const smallH = Math.max(1, Math.round(h * scale))
  const small = createCanvas(smallW, smallH)
  context(small).drawImage(canvas, x, y, w, h, 0, 0, smallW, smallH)
  ctx.imageSmoothingEnabled = false
  ctx.drawImage(small, 0, 0, smallW, smallH, x, y, w, h)
  ctx.imageSmoothingEnabled = true
}

/** Render the edited image onto a new canvas, ready to preview or upload. */
export function renderRedacted(source: Source, edits: Edits, createCanvas: CanvasFactory = browserCanvas): CanvasLike {
  const rotated = rotate(source, edits.rotation, createCanvas)
  const crop = clampRect(edits.crop ?? { x: 0, y: 0, w: 1, h: 1 })
  const cropX = Math.round(crop.x * rotated.width)
  const cropY = Math.round(crop.y * rotated.height)
  const cropW = Math.max(1, Math.round(crop.w * rotated.width))
  const cropH = Math.max(1, Math.round(crop.h * rotated.height))
  const scale = Math.min(1, MAX_OUTPUT / Math.max(cropW, cropH))

  const output = createCanvas(Math.max(1, Math.round(cropW * scale)), Math.max(1, Math.round(cropH * scale)))
  const ctx = context(output)
  ctx.drawImage(rotated, cropX, cropY, cropW, cropH, 0, 0, output.width, output.height)

  for (const redaction of edits.redactions) {
    const r = clampRect(redaction)
    const x = Math.round(r.x * output.width)
    const y = Math.round(r.y * output.height)
    const w = Math.max(1, Math.round(r.w * output.width))
    const h = Math.max(1, Math.round(r.h * output.height))
    if (redaction.mode === 'fill') {
      ctx.fillStyle = FILL_COLOUR
      ctx.fillRect(x, y, w, h)
    } else {
      pixelate(ctx, output, x, y, w, h, createCanvas)
    }
  }
  return output
}

export function canvasToBlob(canvas: CanvasLike, quality = JPEG_QUALITY): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error('The image could not be prepared.'))),
      'image/jpeg',
      quality,
    )
  })
}

/** Decode a picked file on the device, honouring its orientation. */
export async function loadSource(file: Blob): Promise<ImageBitmap> {
  return createImageBitmap(file, { imageOrientation: 'from-image' })
}

/** The only path from an edited image to an upload: render, then encode. */
export async function exportRedacted(source: Source, edits: Edits): Promise<Blob> {
  return canvasToBlob(renderRedacted(source, edits))
}

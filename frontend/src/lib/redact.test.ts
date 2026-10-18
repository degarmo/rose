import { describe, expect, it } from 'vitest'
import {
  canvasToBlob,
  FILL_COLOUR,
  MAX_OUTPUT,
  PIXEL_BLOCKS,
  rectFromPoints,
  renderRedacted,
  type CanvasLike,
  type Context2D,
} from './redact'

interface FakeCanvas extends CanvasLike {
  ops: Array<{ op: string; args: unknown[]; smoothing?: boolean; fill?: unknown }>
}

function fakeCanvases() {
  const created: FakeCanvas[] = []
  const factory = (width: number, height: number): FakeCanvas => {
    const ops: FakeCanvas['ops'] = []
    const ctx: Context2D = {
      fillStyle: '',
      imageSmoothingEnabled: true,
      drawImage: (...args: unknown[]) => ops.push({ op: 'drawImage', args, smoothing: ctx.imageSmoothingEnabled }),
      fillRect: (...args: number[]) => ops.push({ op: 'fillRect', args, fill: ctx.fillStyle }),
      translate: (...args: number[]) => ops.push({ op: 'translate', args }),
      rotate: (...args: number[]) => ops.push({ op: 'rotate', args }),
    }
    const canvas: FakeCanvas = {
      width,
      height,
      ops,
      getContext: () => ctx,
      toBlob: (callback, type) => callback(new Blob([`rendered ${width}x${height}`], { type })),
    }
    created.push(canvas)
    return canvas
  }
  return { factory, created }
}

const photo = { width: 1000, height: 500, marker: 'ORIGINAL' }

describe('renderRedacted', () => {
  it('draws the source once, onto a rotation canvas, never straight onto the output', () => {
    const { factory, created } = fakeCanvases()
    const output = renderRedacted(photo, { rotation: 0, crop: null, redactions: [] }, factory) as FakeCanvas
    const [rotated] = created
    expect(rotated.ops.find((o) => o.op === 'drawImage')?.args[0]).toBe(photo)
    expect(output.ops.every((o) => o.args[0] !== photo)).toBe(true)
    expect(output.ops[0].args[0]).toBe(rotated)
    expect([output.width, output.height]).toEqual([1000, 500])
  })

  it('covers a region with a solid fill in output coordinates', () => {
    const { factory } = fakeCanvases()
    const output = renderRedacted(
      photo,
      { rotation: 0, crop: null, redactions: [{ x: 0.1, y: 0.2, w: 0.3, h: 0.4, mode: 'fill' }] },
      factory,
    ) as FakeCanvas
    const fill = output.ops.find((o) => o.op === 'fillRect')
    expect(fill).toEqual({ op: 'fillRect', args: [100, 100, 300, 200], fill: FILL_COLOUR })
  })

  it('pixelates through a tiny canvas scaled back up without smoothing', () => {
    const { factory, created } = fakeCanvases()
    const output = renderRedacted(
      photo,
      { rotation: 0, crop: null, redactions: [{ x: 0.5, y: 0, w: 0.5, h: 1, mode: 'pixelate' }] },
      factory,
    ) as FakeCanvas
    const small = created.find((c) => Math.max(c.width, c.height) === PIXEL_BLOCKS)
    expect(small).toBeDefined()
    expect(small?.ops[0].args[0]).toBe(output)
    const upscale = output.ops.find((o) => o.op === 'drawImage' && o.args[0] === small)
    expect(upscale?.smoothing).toBe(false)
    expect(upscale?.args.slice(5)).toEqual([500, 0, 500, 500])
  })

  it('rotates a quarter turn by swapping width and height', () => {
    const { factory } = fakeCanvases()
    const output = renderRedacted(photo, { rotation: 90, crop: null, redactions: [] }, factory)
    expect([output.width, output.height]).toEqual([500, 1000])
  })

  it('crops before redacting and caps the longest side', () => {
    const { factory } = fakeCanvases()
    const big = { width: 6000, height: 3000 }
    const output = renderRedacted(big, { rotation: 0, crop: { x: 0.5, y: 0, w: 0.5, h: 1 }, redactions: [] }, factory) as FakeCanvas
    expect(Math.max(output.width, output.height)).toBe(MAX_OUTPUT)
    expect(output.ops[0].args.slice(1, 5)).toEqual([3000, 0, 3000, 3000])
  })

  it('encodes the rendered canvas as JPEG', async () => {
    const { factory } = fakeCanvases()
    const blob = await canvasToBlob(renderRedacted(photo, { rotation: 0, crop: null, redactions: [] }, factory))
    expect(blob.type).toBe('image/jpeg')
    expect(await blob.text()).toBe('rendered 1000x500')
  })

  it('normalises a drag in any direction', () => {
    expect(rectFromPoints(0.8, 0.9, 0.2, 0.1)).toEqual({ x: 0.2, y: 0.1, w: expect.closeTo(0.6), h: expect.closeTo(0.8) })
    expect(rectFromPoints(-1, -1, 2, 2)).toEqual({ x: 0, y: 0, w: 1, h: 1 })
  })
})

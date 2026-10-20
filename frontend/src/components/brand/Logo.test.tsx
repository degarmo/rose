import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AgeGate } from '@/components/layout/AgeGate'
import { Logo } from './Logo'

describe('Logo', () => {
  it('offers WebP with a PNG fallback, at a fixed size', () => {
    const { container } = render(<Logo height={44} />)
    const source = container.querySelector('picture > source')
    const image = container.querySelector('picture > img')
    expect(source).toHaveAttribute('type', 'image/webp')
    expect(source?.getAttribute('srcset')).toBe(
      '/brand/emblem-120.webp 120w, /brand/emblem-240.webp 240w, /brand/emblem-480.webp 480w, /brand/emblem-960.webp 960w',
    )
    expect(image).toHaveAttribute('src', '/brand/emblem-240.png')
    expect(image?.getAttribute('srcset')).toContain('/brand/emblem-960.png 960w')
    expect(image).toHaveAttribute('width', '91')
    expect(image).toHaveAttribute('height', '44')
    expect(image).toHaveAttribute('sizes', '91px')
    expect(image).toHaveAttribute('loading', 'lazy')
  })

  it('draws the square rose for the mark, fetched at once when it leads the page', () => {
    const { container } = render(<Logo variant="mark" height={28} priority decorative />)
    const image = container.querySelector('img')
    expect(image).toHaveAttribute('src', '/brand/rose-128.png')
    expect(image).toHaveAttribute('width', '28')
    expect(image).toHaveAttribute('alt', '')
    expect(image).toHaveAttribute('loading', 'eager')
  })

  it('asks, on the age gate, for exactly what the server preloads (apps/core/spa.py, GATE_EMBLEM)', () => {
    const { container } = render(<AgeGate onConfirm={() => {}} onDecline={() => {}} />)
    const source = container.querySelector('picture > source')
    expect(source).toHaveAttribute('sizes', '247px')
    expect(source?.getAttribute('srcset')).toBe(
      '/brand/emblem-120.webp 120w, /brand/emblem-240.webp 240w, /brand/emblem-480.webp 480w, /brand/emblem-960.webp 960w',
    )
  })

  it('never points at anything outside the generated files', () => {
    const { container } = render(<Logo height={120} sizes="247px" />)
    const urls = [...container.querySelectorAll('[srcset], [src]')].flatMap((element) =>
      [element.getAttribute('src') ?? '', ...(element.getAttribute('srcset') ?? '').split(', ')].filter(Boolean),
    )
    expect(urls.every((url) => url.startsWith('/brand/'))).toBe(true)
    expect(container.querySelector('source')).toHaveAttribute('sizes', '247px')
  })
})

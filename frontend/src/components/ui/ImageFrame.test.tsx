import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ImageFrame } from './ImageFrame'

const picture = { url: '/media/a.webp', alt: 'A red archway', width: 1920, height: 1280, srcset: '/media/a-640w.webp 640w, /media/a.webp 1920w' }

describe('ImageFrame', () => {
  it('shows the picture with its own description, size and srcset', () => {
    render(<ImageFrame remote={picture} alt="" sizes="50vw" />)
    const image = screen.getByRole('img', { name: 'A red archway' })
    expect(image).toHaveAttribute('srcset', picture.srcset)
    expect(image).toHaveAttribute('sizes', '50vw')
    expect(image).toHaveAttribute('width', '1920')
    expect(image).toHaveAttribute('height', '1280')
  })

  it('keeps the focal point in view as it crops', () => {
    render(<ImageFrame remote={picture} alt="" focal={{ x: 0.25, y: 0.8 }} />)
    expect(screen.getByRole('img')).toHaveStyle({ objectPosition: '25% 80%' })
  })

  it('loads lazily unless it is above the fold', () => {
    const { rerender } = render(<ImageFrame remote={picture} alt="" />)
    expect(screen.getByRole('img')).toHaveAttribute('loading', 'lazy')
    rerender(<ImageFrame remote={picture} alt="" priority />)
    expect(screen.getByRole('img')).toHaveAttribute('loading', 'eager')
  })

  it('shows only the texture when there is no picture', () => {
    const { container } = render(<ImageFrame remote={null} alt="" placeholder="warm" />)
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('.wash-warm')).not.toBeNull()
  })
})

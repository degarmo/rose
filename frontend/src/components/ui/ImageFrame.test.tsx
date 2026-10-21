import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import manifest from '@image-manifest'
import { ImageFrame } from './ImageFrame'

const images = (manifest as { images: Array<{ filename: string; alt?: string }> }).images

describe('ImageFrame', () => {
  it.each(images.map((image) => [image.filename, image.alt]))('describes %s from the manifest', (filename, alt) => {
    expect(alt).toBeTruthy()
    render(<ImageFrame image={filename} alt="" />)
    expect(screen.getByRole('img')).toHaveAttribute('alt', alt)
  })

  it('keeps alt text a page gives it', () => {
    render(<ImageFrame image="home-hero.webp" alt="The club at night" />)
    expect(screen.getByRole('img', { name: 'The club at night' })).toBeInTheDocument()
  })

  it('shows only the placeholder for an image that is not in the manifest', () => {
    const { container } = render(<ImageFrame image="missing.webp" alt="" />)
    expect(container.querySelector('img')).toBeNull()
  })
})

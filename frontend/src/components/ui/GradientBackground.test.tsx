import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { GradientBackground } from './GradientBackground'

describe('GradientBackground', () => {
  it('is a decorative layer behind its section', () => {
    const { container } = render(<GradientBackground className="opacity-90" />)
    const layer = container.firstElementChild!
    expect(layer).toHaveAttribute('aria-hidden', 'true')
    expect(layer).toHaveClass('gradient-aurora', 'absolute', 'inset-0', '-z-10', 'opacity-90')
    expect(layer).toBeEmptyDOMElement()
  })
})

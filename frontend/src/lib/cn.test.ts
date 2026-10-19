import { describe, expect, it } from 'vitest'
import { cn } from './cn'

describe('cn', () => {
  it('lets later classes override earlier ones', () => {
    expect(cn('inline-flex px-3 py-1', 'hidden lg:inline-flex px-3.5')).toBe('py-1 hidden lg:inline-flex px-3.5')
    expect(cn('h-10 px-5', false, 'h-11')).toBe('px-5 h-11')
  })

  it('knows the design tokens are sizes, corners and shadows, not colours', () => {
    expect(cn('text-h1', 'text-fg')).toBe('text-h1 text-fg')
    expect(cn('text-fg', 'lg:text-card-title', 'text-xl')).toBe('text-fg lg:text-card-title text-xl')
    expect(cn('rounded-full', 'rounded-card')).toBe('rounded-card')
    expect(cn('shadow-sheet', 'shadow-modal')).toBe('shadow-modal')
    expect(cn('text-meta', 'text-sm')).toBe('text-sm')
  })
})

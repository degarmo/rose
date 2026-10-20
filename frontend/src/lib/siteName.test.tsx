import { render, renderHook, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// The server writes the names into the page; "Chicago" stands in for a name that
// must never reach a discreet place.
const NAMES = { 'display-name': 'The Chicago Example', 'short-name': 'Chicago Example', 'neutral-name': 'Rose' }

function writeNames() {
  for (const [name, content] of Object.entries(NAMES)) {
    const meta = document.createElement('meta')
    meta.name = `rose-site-${name}`
    meta.content = content
    document.head.appendChild(meta)
  }
}

/** The modules read the page once, when first imported. */
async function load() {
  vi.resetModules()
  const [{ config }, meta, { Wordmark }, primitives] = await Promise.all([
    import('./config'),
    import('./useDocumentMeta'),
    import('@/components/layout/Wordmark'),
    import('@/components/members/app/primitives'),
  ])
  return { config, ...meta, Wordmark, MemberWordmark: primitives.Wordmark }
}

beforeEach(writeNames)

afterEach(() => {
  document.head.querySelectorAll('meta[name^="rose-site-"]').forEach((meta) => meta.remove())
  window.history.replaceState(null, '', '/')
})

describe('the club name', () => {
  it('comes from the page', async () => {
    const { config } = await load()
    expect(config.displayName).toBe('The Chicago Example')
    expect(config.shortName).toBe('Chicago Example')
    expect(config.neutralName).toBe('Rose')
  })

  it('falls back to the display name for the short form, and to Rose', async () => {
    document.head.querySelector('meta[name="rose-site-short-name"]')?.remove()
    expect((await load()).config.shortName).toBe('The Chicago Example')
    document.head.querySelectorAll('meta[name^="rose-site-"]').forEach((meta) => meta.remove())
    const { config } = await load()
    expect([config.displayName, config.shortName, config.neutralName]).toEqual(['Rose', 'Rose', 'Rose'])
  })

  it('titles public pages with the display name', async () => {
    const { useDocumentMeta } = await load()
    window.history.replaceState(null, '', '/visit')
    renderHook(() => useDocumentMeta({ title: 'Visit' }))
    expect(document.title).toBe('Visit | The Chicago Example')
  })

  it.each(['/members', '/members/feed', '/members/staff/door'])('keeps the tab neutral on %s', async (path) => {
    const { useDocumentMeta, tabName } = await load()
    window.history.replaceState(null, '', path)
    renderHook(() => useDocumentMeta({ title: 'Feed' }))
    expect(document.title).toBe('Feed | Rose')
    expect(tabName(path)).not.toContain('Chicago')
  })

  it('treats only the member app as private to the tab', async () => {
    const { tabName } = await load()
    expect(tabName('/membership')).toBe('The Chicago Example')
  })

  it('shows the short form on phones and the full name from the small breakpoint up', async () => {
    const { Wordmark } = await load()
    render(
      <MemoryRouter>
        <Wordmark />
      </MemoryRouter>,
    )
    expect(screen.getByText('Chicago Example')).toHaveClass('sm:hidden')
    expect(screen.getByText('The Chicago Example')).toHaveClass('hidden', 'sm:inline')
    expect(screen.getByRole('link')).toHaveClass('whitespace-nowrap')
  })

  it('uses the short form in the member sidebar', async () => {
    const { MemberWordmark } = await load()
    const { container } = render(<MemberWordmark />)
    expect(container).toHaveTextContent(/^Chicago Example$/)
  })
})

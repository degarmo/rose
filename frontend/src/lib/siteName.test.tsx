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
  const [{ config }, meta, { Logo }, primitives] = await Promise.all([
    import('./config'),
    import('./useDocumentMeta'),
    import('@/components/brand/Logo'),
    import('@/components/members/app/primitives'),
  ])
  return { config, ...meta, Logo, RoseMark: primitives.RoseMark }
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

  it('names the logo with the display name, linking Home in the header', async () => {
    const { Logo } = await load()
    render(
      <MemoryRouter>
        <Logo to="/" height={44} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: 'The Chicago Example' })).toHaveAttribute('href', '/')
  })

  it('gives the club avatar no alt text of its own: the name is beside it', async () => {
    const { RoseMark } = await load()
    const { container } = render(<RoseMark />)
    expect(container.querySelector('img')).toHaveAttribute('alt', '')
    expect(container).not.toHaveTextContent('Chicago')
  })
})

import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { describe, expect, it } from 'vitest'
import { ToastProvider } from '@/components/ui'
import type { Account } from '@/lib/api'
import { verifiedUser } from '@/test/render'
import { AuthContext, type AuthState } from './authContext'
import { Layout } from './Layout'
import { SiteSettingsContext, type SiteSettingsState } from './siteSettingsContext'

const settings = { status: 'loading', retry: () => undefined } as SiteSettingsState

function renderSite(user: Account | null, path = '/events') {
  const auth: AuthState = { status: 'ready', user, applySession: () => undefined, refresh: async () => undefined, logout: async () => undefined }
  const router = createMemoryRouter([{ path: '/', element: <Layout />, children: [{ path: '*', element: <p>Page body</p> }] }], {
    initialEntries: [path],
  })
  render(
    <SiteSettingsContext.Provider value={settings}>
      <AuthContext.Provider value={auth}>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </AuthContext.Provider>
    </SiteSettingsContext.Provider>,
  )
}

const people: Array<[string, Account | null]> = [
  ['logged out', null],
  ['logged in', verifiedUser],
  ['a member', { ...verifiedUser, has_membership: true, feed_access: true }],
]

describe('website header and footer', () => {
  it.each(people)('shows Membership where Journal was, for someone %s', (_, user) => {
    renderSite(user)
    const nav = within(screen.getByRole('banner')).getByRole('navigation', { name: 'Main' })
    const labels = within(nav)
      .getAllByRole('link')
      .map((link) => link.textContent)
    expect(labels.slice(0, 3)).toEqual(['About', 'Events', 'Education'])
    expect(labels[3]).toBe('Membership')
    expect(within(nav).getByRole('link', { name: 'Membership' })).toHaveAttribute('href', '/membership')
    expect(within(nav).queryByRole('link', { name: 'Journal' })).not.toBeInTheDocument()
    // "Join" stays, for everyone, and opens the plans.
    expect(within(screen.getByRole('banner')).getByRole('link', { name: 'Join' })).toHaveAttribute('href', '/membership')
  })

  it.each(people)('has Membership and no Journal in the phone menu, for someone %s', async (_, user) => {
    renderSite(user)
    await userEvent.click(screen.getByRole('button', { name: 'Open menu' }))
    const menu = screen.getByRole('dialog', { name: 'Menu' })
    expect(within(menu).getByRole('link', { name: 'Membership' })).toHaveAttribute('href', '/membership')
    expect(within(menu).queryByRole('link', { name: 'Journal' })).not.toBeInTheDocument()
    expect(within(menu).getByRole('link', { name: 'Join' })).toHaveAttribute('href', '/membership')
  })

  it.each(['/', '/events'])('keeps Journal reachable from the footer on %s', (path) => {
    renderSite(null, path)
    const footer = screen.getByRole('contentinfo')
    expect(within(footer).getByRole('link', { name: 'Journal' })).toHaveAttribute('href', '/journal')
    expect(within(footer).getByRole('link', { name: 'Membership' })).toHaveAttribute('href', '/membership')
    expect(within(footer).getByRole('link', { name: 'Privacy' })).toHaveAttribute('href', '/privacy')
  })
})

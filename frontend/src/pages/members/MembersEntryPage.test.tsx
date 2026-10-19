import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { describe, expect, it } from 'vitest'
import { AuthContext, type AuthState } from '@/components/layout/authContext'
import { SiteSettingsContext, type SiteSettingsState } from '@/components/layout/siteSettingsContext'
import { ToastProvider } from '@/components/ui'
import type { Account } from '@/lib/api'
import { landingAfterLogin, memberAppPath } from '@/lib/memberApp'
import { verifiedUser } from '@/test/render'
import { MembersEntryPage } from './MembersEntryPage'

const settings = { status: 'loading', retry: () => undefined } as SiteSettingsState

function renderEntry(user: Account | null) {
  const auth: AuthState = { status: 'ready', user, applySession: () => undefined, refresh: async () => undefined, logout: async () => undefined }
  const router = createMemoryRouter(
    [
      { path: '/members', element: <MembersEntryPage /> },
      { path: '/members/feed', element: <p>The feed</p> },
      { path: '/members/join-feed', element: <p>Join the feed</p> },
    ],
    { initialEntries: ['/members'] },
  )
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

describe('/members', () => {
  it('opens the feed for members whose app is open', () => {
    renderEntry({ ...verifiedUser, feed_access: true, member_app: 'open' })
    expect(screen.getByText('The feed')).toBeInTheDocument()
  })

  it('takes members who may join to joining', () => {
    renderEntry({ ...verifiedUser, member_app: 'join' })
    expect(screen.getByText('Join the feed')).toBeInTheDocument()
  })

  it('explains and links to the plans for anyone else signed in', () => {
    renderEntry(verifiedUser)
    expect(screen.getByRole('heading', { name: 'The member app comes with membership' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'See membership plans' })).toHaveAttribute('href', '/membership')
  })

  it('points a paused member to their account', () => {
    renderEntry({ ...verifiedUser, member_app: 'paused' })
    expect(screen.getByRole('link', { name: 'See my notices' })).toHaveAttribute('href', '/members/settings/notices')
  })

  it('is the ordinary 404 when signed out', () => {
    renderEntry(null)
    expect(screen.getByRole('heading', { name: 'This room is not on the map.' })).toBeInTheDocument()
  })
})

describe('getting into the app', () => {
  it('lands the team on the staff dashboard, open-app members in the feed and everyone else on Home, unless they came from a page', () => {
    const open = { member_app: 'open' as const, staff: null }
    expect(landingAfterLogin(open, null, '/members/home')).toBe('/members/feed')
    expect(landingAfterLogin(open, '/', '/')).toBe('/members/feed')
    expect(landingAfterLogin(open, '/events/x', '/events/x')).toBe('/events/x')
    for (const member_app of ['join', 'paused', null] as const) {
      expect(landingAfterLogin({ member_app, staff: null }, null, '/members/home')).toBe('/members/home')
    }
    const owner = { member_app: 'open' as const, staff: { role: 'admin' as const, verified: false, verify_url: '/v', needs_enrollment: true, admin_url: '/a', door_desk_url: null } }
    expect(landingAfterLogin(owner, null, '/members/home')).toBe('/members/staff')
    expect(landingAfterLogin(owner, '/events/x', '/events/x')).toBe('/events/x')
    expect(memberAppPath({ member_app: 'open' })).toBe('/members/feed')
    expect(memberAppPath({ member_app: 'join' })).toBe('/members/join-feed')
    expect(memberAppPath({ member_app: null })).toBe('/members/home')
  })
})

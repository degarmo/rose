import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { Account } from '@/lib/api'
import { renderWithProviders, verifiedUser } from '@/test/render'
import { AccountMenu } from './AccountMenu'

async function open(user: Account) {
  renderWithProviders(<AccountMenu />, { user })
  await userEvent.click(screen.getByRole('button', { name: user.display_name }))
}

describe('AccountMenu', () => {
  it('offers the member app to members who have it', async () => {
    await open({ ...verifiedUser, feed_access: true, member_app: 'open' })
    expect(screen.getByRole('link', { name: 'Member app' })).toHaveAttribute('href', '/members/feed')
    expect(screen.queryByRole('link', { name: 'Staff' })).not.toBeInTheDocument()
  })

  it('offers joining to members who may join', async () => {
    await open({ ...verifiedUser, member_app: 'join' })
    expect(screen.getByRole('link', { name: 'Member app' })).toHaveAttribute('href', '/members/join-feed')
  })

  it('takes people without the feed to Home, and everyone to Settings', async () => {
    await open(verifiedUser)
    expect(screen.getByRole('link', { name: 'Member app' })).toHaveAttribute('href', '/members/home')
    expect(screen.getByRole('link', { name: 'Settings' })).toHaveAttribute('href', '/members/settings')
    expect(screen.queryByRole('list', { name: 'Staff' })).not.toBeInTheDocument()
  })

  it('gives the team a Staff block with every way in', async () => {
    await open({
      ...verifiedUser,
      member_app: 'open',
      staff: {
        role: 'admin',
        door_desk: true,
        verified: true,
        verify_url: null,
        needs_enrollment: false,
        admin_url: 'https://site.example/admin/', age_check_required: true, can_change_age_check: false, age_check_url: 'https://site.example/admin/pages/sitesettings/age-verification/',
      },
    })
    const block = screen.getByRole('list', { name: 'Staff' })
    expect(screen.getByText('Admin')).toBeInTheDocument()
    const links = Object.fromEntries(within(block).getAllByRole('link').map((link) => [link.textContent, link.getAttribute('href')]))
    expect(links).toEqual({
      Dashboard: 'https://site.example/admin/',
      Reports: '/members/staff/reports',
      'Door desk': '/members/staff/door',
      'Member app': '/members/feed',
      Website: '/',
    })
  })

  it('gives a door volunteer the door desk and nothing for a team role', async () => {
    await open({
      ...verifiedUser,
      staff: {
        role: null,
        door_desk: true,
        verified: true,
        verify_url: null,
        needs_enrollment: false,
        admin_url: 'https://site.example/admin/', age_check_required: true, can_change_age_check: false, age_check_url: 'https://site.example/admin/pages/sitesettings/age-verification/',
      },
    })
    const block = screen.getByRole('list', { name: 'Staff' })
    const links = within(block).getAllByRole('link').map((link) => link.textContent)
    expect(links[0]).toBe('Door desk')
    expect(links).not.toContain('Dashboard')
    expect(links).not.toContain('Reports')
  })
})

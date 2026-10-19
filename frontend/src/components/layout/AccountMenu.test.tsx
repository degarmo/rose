import { screen } from '@testing-library/react'
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

  it('has no app link for people without it, and Staff only for the team', async () => {
    await open({ ...verifiedUser, staff: { role: 'moderator', verified: false, verify_url: '/x' } })
    expect(screen.queryByRole('link', { name: 'Member app' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Staff' })).toHaveAttribute('href', '/members/staff')
  })
})

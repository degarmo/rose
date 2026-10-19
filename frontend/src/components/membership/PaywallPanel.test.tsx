import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderWithProviders, verifiedUser } from '@/test/render'
import { PaywallPanel } from './PaywallPanel'

const props = { title: 'For members', benefit: 'The full description is in the member area.' }

describe('PaywallPanel', () => {
  it('asks anonymous visitors to join or log in', () => {
    renderWithProviders(<PaywallPanel {...props} />, { path: '/education/advanced-lab' })
    expect(screen.getByRole('heading', { level: 3, name: 'For members' })).toBeInTheDocument()
    expect(screen.getByText(props.benefit)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Join' })).toHaveAttribute('href', '/membership')
    expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/account/login?next=%2Feducation%2Fadvanced-lab')
  })

  it('offers membership to signed-in people without one', () => {
    renderWithProviders(<PaywallPanel {...props} tiers={['Monthly', 'Annual']} />, { user: verifiedUser })
    expect(screen.getByRole('link', { name: 'Join' })).toHaveAttribute('href', '/membership')
    expect(screen.getByText('Included with Monthly and Annual memberships.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Log in' })).not.toBeInTheDocument()
  })

  it('sends people with a membership to their account', () => {
    renderWithProviders(<PaywallPanel {...props} tiers={['Monthly']} />, { user: { ...verifiedUser, has_membership: true } })
    expect(screen.getByRole('link', { name: 'See my membership' })).toHaveAttribute('href', '/account#membership')
    expect(screen.getByText(/does not include this, or is not active/)).toBeInTheDocument()
    expect(screen.getByText('Included with Monthly membership.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Join' })).not.toBeInTheDocument()
  })

  it('takes a page-level heading when it stands alone', () => {
    renderWithProviders(<PaywallPanel {...props} size="lg" headingLevel="h2" />, { user: verifiedUser })
    expect(screen.getByRole('heading', { level: 2, name: 'For members' })).toBeInTheDocument()
  })
})

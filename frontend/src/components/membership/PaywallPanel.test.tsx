import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderWithProviders, verifiedUser } from '@/test/render'
import { PaywallPanel } from './PaywallPanel'

const props = { title: 'For members', benefit: 'Members-only classes come with membership.' }

describe('PaywallPanel', () => {
  it('asks anonymous visitors to log in or create an account', () => {
    renderWithProviders(<PaywallPanel {...props} />, { path: '/education/advanced-lab' })
    expect(screen.getByRole('heading', { name: 'For members' })).toBeInTheDocument()
    expect(screen.getByText(props.benefit)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/account/login?next=%2Feducation%2Fadvanced-lab')
    expect(screen.getByRole('link', { name: 'Create an account' })).toHaveAttribute('href', '/account/register?next=%2Fjoin')
    expect(screen.queryByRole('link', { name: 'Become a member' })).not.toBeInTheDocument()
  })

  it('offers membership to signed-in people without one', () => {
    renderWithProviders(<PaywallPanel {...props} tiers={['Monthly', 'Annual']} />, { user: verifiedUser })
    expect(screen.getByRole('link', { name: 'Become a member' })).toHaveAttribute('href', '/join')
    expect(screen.getByText('Included with Monthly and Annual memberships.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Log in' })).not.toBeInTheDocument()
  })

  it('sends people with a membership to their account', () => {
    renderWithProviders(<PaywallPanel {...props} tiers={['Monthly']} />, { user: { ...verifiedUser, has_membership: true } })
    expect(screen.getByRole('link', { name: 'See my membership' })).toHaveAttribute('href', '/account#membership')
    expect(screen.getByText(/does not include this, or is not active/)).toBeInTheDocument()
    expect(screen.getByText('Included with Monthly membership.')).toBeInTheDocument()
  })

  it('has an inline variant without its own card', () => {
    renderWithProviders(<PaywallPanel {...props} variant="inline" headingLevel="h3" />, { user: verifiedUser })
    const panel = screen.getByTestId('paywall')
    expect(panel.tagName).toBe('DIV')
    expect(screen.getByRole('heading', { level: 3, name: 'For members' })).toBeInTheDocument()
  })
})

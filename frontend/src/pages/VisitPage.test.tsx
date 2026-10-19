import { screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SiteSettingsContext, type SiteSettingsState } from '@/components/layout/siteSettingsContext'
import type { SiteSettings } from '@/lib/api'
import { renderWithProviders } from '@/test/render'
import { VisitPage } from './VisitPage'

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return { ...actual, api: { ...actual.api, faqs: () => Promise.resolve([]) } }
})

function renderVisit(overrides: Partial<SiteSettings>) {
  const data = {
    tagline: '',
    hours_text: '',
    address_text: '',
    directions_text: '',
    phone_text: '',
    contact_email: 'hello@example.org',
    quick_exit_url: '',
    nonprofit_status_text: '',
    social_links: [],
    ...overrides,
  } as SiteSettings
  const settings = { status: 'success', data, retry: () => undefined } as SiteSettingsState
  renderWithProviders(
    <SiteSettingsContext.Provider value={settings}>
      <VisitPage />
    </SiteSettingsContext.Provider>,
  )
}

describe('VisitPage directions', () => {
  it('shows the address and phone number, then the directions', () => {
    renderVisit({
      address_text: '100 Example St\nChicago, IL 60600',
      phone_text: '(312) 555-0100',
      directions_text: 'Take the #22 bus.\n\nThe entrance is at the back.',
    })
    expect(screen.getByText('Address:').nextSibling).toHaveTextContent('100 Example St, Chicago, IL 60600')
    expect(screen.getByRole('link', { name: '(312) 555-0100' })).toHaveAttribute('href', 'tel:3125550100')
    expect(screen.getByText('Directions:')).toBeInTheDocument()
    expect(screen.getByText(/Take the #22 bus\./)).toHaveTextContent('The entrance is at the back.')
  })

  it('leaves out what is not set', () => {
    renderVisit({ directions_text: 'Take the #22 bus.' })
    expect(screen.queryByText('Address:')).not.toBeInTheDocument()
    expect(screen.queryByText('Phone Number:')).not.toBeInTheDocument()
    expect(screen.getByText('Take the #22 bus.')).toBeInTheDocument()
  })

  it('says directions are shared later when nothing is set', () => {
    renderVisit({})
    expect(screen.getByText('Directions are shared with confirmed visitors.')).toBeInTheDocument()
  })
})

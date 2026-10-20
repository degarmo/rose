import { screen } from '@testing-library/react'
import { Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EventDetail } from '@/lib/api'
import { renderWithProviders, verifiedUser } from '@/test/render'
import { EventPage } from './EventPage'

const apiMock = vi.hoisted(() => ({ event: vi.fn() }))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return { ...actual, api: { ...actual.api, ...apiMock } }
})

function makeEvent(extra: Partial<EventDetail> = {}): EventDetail {
  return {
    id: 1,
    slug: 'friday-social',
    title: 'Friday Social',
    summary: 'Summary',
    category: 'social',
    category_label: 'Social',
    audience: 'public',
    starts_at: '2026-11-06T21:00:00-06:00',
    ends_at: '2026-11-07T01:00:00-06:00',
    timing: 'upcoming',
    location_label: 'Main floor',
    hero_image: null,
    rsvp: {
      state: 'open',
      can_rsvp: true,
      reason: 'ok',
      opens_at: null,
      closes_at: '2026-11-06T21:00:00-06:00',
      max_party_size: 2,
      plan_party_limit: null,
      events_remaining: null,
      mine: null,
    },
    attendee_count: null,
    body: '<p>An evening of dancing.</p>',
    opportunity: null,
    ...extra,
  }
}

function renderEvent() {
  renderWithProviders(
    <Routes>
      <Route path="/events/:slug" element={<EventPage />} />
    </Routes>,
    { user: verifiedUser, path: '/events/friday-social' },
  )
}

function robots() {
  return document.head.querySelector('meta[name="robots"]')?.getAttribute('content')
}

beforeEach(() => apiMock.event.mockReset())

describe('EventPage', () => {
  it('shows the RSVP panel while the event is still to come, and may be indexed', async () => {
    apiMock.event.mockResolvedValue(makeEvent())
    renderEvent()
    expect(await screen.findByRole('heading', { name: 'Friday Social', level: 1 })).toBeInTheDocument()
    expect(screen.queryByText('This event has passed')).not.toBeInTheDocument()
    expect(screen.getByRole('complementary')).toBeInTheDocument()
    expect(robots()).toBe('index, follow')
  })

  it('says a past event has passed, with no RSVP panel, a way to what is next, and noindex', async () => {
    apiMock.event.mockResolvedValue(
      makeEvent({ timing: 'past', rsvp: { ...makeEvent().rsvp, state: 'past', can_rsvp: false, reason: 'past' } }),
    )
    renderEvent()
    expect(await screen.findByRole('heading', { name: 'This event has passed' })).toBeInTheDocument()
    expect(screen.getByText('An evening of dancing.')).toBeInTheDocument()
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /RSVP/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Upcoming socials' })).toHaveAttribute('href', '/events?category=social')
    expect(robots()).toBe('noindex, nofollow')
  })

  it('shows only the start time when no end time was given', async () => {
    apiMock.event.mockResolvedValue(makeEvent({ ends_at: null }))
    renderEvent()
    expect(await screen.findByText(/Nov 6 · 9:00 PM$/)).toBeInTheDocument()
  })
})

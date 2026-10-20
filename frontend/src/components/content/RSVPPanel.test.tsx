import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EventDetail, RSVPState } from '@/lib/api'
import { renderWithProviders, unverifiedUser, verifiedUser } from '@/test/render'
import { RSVPPanel } from './RSVPPanel'

const apiMock = vi.hoisted(() => ({
  rsvp: vi.fn(),
  cancelRSVP: vi.fn(),
  resendVerification: vi.fn(),
  icsUrl: (slug: string, details: boolean) => `/api/events/${slug}/calendar.ics${details ? '?details=1' : ''}`,
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return { ...actual, api: { ...actual.api, ...apiMock } }
})

function rsvpState(overrides: Partial<RSVPState> = {}): RSVPState {
  return {
    state: 'open',
    can_rsvp: true,
    reason: 'ok',
    opens_at: null,
    closes_at: '2026-11-05T19:00:00-06:00',
    max_party_size: 2,
    plan_party_limit: null,
    events_remaining: null,
    mine: null,
    ...overrides,
  }
}

function makeEvent(rsvp: Partial<RSVPState> = {}, extra: Partial<EventDetail> = {}): EventDetail {
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
    image_fallback: 'social',
    rsvp: rsvpState(rsvp),
    attendee_count: null,
    body: '<p>Body</p>',
    opportunity: null,
    ...extra,
  }
}

function renderPanel(event: EventDetail, user = verifiedUser as typeof verifiedUser | null) {
  const onChange = vi.fn()
  renderWithProviders(<RSVPPanel event={event} onChange={onChange} />, { user })
  return { onChange }
}

beforeEach(() => {
  apiMock.rsvp.mockReset()
  apiMock.cancelRSVP.mockReset()
  apiMock.resendVerification.mockReset()
})

describe('RSVPPanel', () => {
  it('asks signed-out visitors to log in or register and come back', () => {
    renderPanel(makeEvent({ can_rsvp: false, reason: 'login_required' }), null)
    expect(screen.getByRole('link', { name: 'Log in to RSVP' })).toHaveAttribute(
      'href',
      '/account/login?next=%2Fevents%2Ffriday-social',
    )
    expect(screen.getByRole('link', { name: /Create an account/ })).toHaveAttribute(
      'href',
      '/account/register?next=%2Fevents%2Ffriday-social',
    )
    expect(screen.queryByRole('form', { name: 'RSVP' })).not.toBeInTheDocument()
  })

  it('offers to resend the verification link to unverified accounts', async () => {
    apiMock.resendVerification.mockResolvedValue({ detail: 'sent' })
    renderPanel(makeEvent({ can_rsvp: false, reason: 'unverified' }), unverifiedUser)
    expect(screen.getByText('Confirm your email')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Send a new link' }))
    expect(apiMock.resendVerification).toHaveBeenCalledOnce()
    expect(await screen.findByText('A new link is on its way.')).toBeInTheDocument()
  })

  it('submits party size and note when open', async () => {
    const going = rsvpState({ state: 'going', mine: { status: 'going', party_size: 2, note_to_hosts: 'Hi' } })
    apiMock.rsvp.mockResolvedValue({ rsvp: going })
    const { onChange } = renderPanel(makeEvent())
    const form = screen.getByRole('form', { name: 'RSVP' })
    await userEvent.click(within(form).getByRole('button', { name: 'One more' }))
    expect(within(form).getByRole('button', { name: 'One more' })).toBeDisabled()
    await userEvent.click(within(form).getByRole('button', { name: 'Add a note for the hosts' }))
    await userEvent.type(within(form).getByLabelText(/Note to hosts/), '  Hi ')
    await userEvent.click(within(form).getByRole('button', { name: 'RSVP for 2' }))
    expect(apiMock.rsvp).toHaveBeenCalledWith('friday-social', 2, 'Hi')
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(going))
    expect(await screen.findByText('You are on the list')).toBeInTheDocument()
  })

  it('disables the button while submitting', async () => {
    let resolve: (value: { rsvp: RSVPState }) => void = () => undefined
    apiMock.rsvp.mockReturnValue(new Promise((r) => (resolve = r)))
    renderPanel(makeEvent())
    await userEvent.click(screen.getByRole('button', { name: 'RSVP' }))
    expect(screen.getByRole('button', { name: 'Saving' })).toBeDisabled()
    resolve({ rsvp: rsvpState({ state: 'going' }) })
    await waitFor(() => expect(screen.getByRole('button', { name: 'RSVP' })).toBeEnabled())
  })

  it('shows an error toast when the RSVP fails', async () => {
    apiMock.rsvp.mockRejectedValue(new Error('This event is full.'))
    renderPanel(makeEvent())
    await userEvent.click(screen.getByRole('button', { name: 'RSVP' }))
    expect(await screen.findByText('Your RSVP was not saved')).toBeInTheDocument()
    expect(screen.getByText('This event is full.')).toBeInTheDocument()
  })

  it('offers the waitlist when full with a waitlist', () => {
    renderPanel(makeEvent({ state: 'waitlist' }))
    expect(screen.getByRole('button', { name: 'Join the waitlist' })).toBeInTheDocument()
  })

  it('hides the single party option when the event allows only one person', () => {
    renderPanel(makeEvent({ max_party_size: 1 }))
    expect(screen.queryByRole('group', { name: 'Party size' })).not.toBeInTheDocument()
  })

  it.each([
    ['full', /waitlist is closed/],
    ['closed', /RSVPs for this evening are closed/],
    ['unavailable', /RSVPs for this evening are closed/],
    ['not_open_yet', /RSVPs open soon/],
  ] as const)('shows the %s state without a form', (state, text) => {
    renderPanel(makeEvent({ state, can_rsvp: false, reason: state === 'full' ? 'ok' : 'closed' }))
    expect(screen.getByText(text)).toBeInTheDocument()
    expect(screen.queryByRole('form', { name: 'RSVP' })).not.toBeInTheDocument()
  })

  it('offers membership to signed-in non-members on a members-only evening', () => {
    renderPanel(makeEvent({ state: 'members_only', can_rsvp: false, reason: 'members_only' }, { audience: 'members' }))
    expect(screen.getByText('Members only')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Join to RSVP' })).toHaveAttribute('href', '/membership')
    expect(screen.queryByRole('link', { name: 'Log in' })).not.toBeInTheDocument()
    expect(screen.queryByRole('form', { name: 'RSVP' })).not.toBeInTheDocument()
  })

  it('asks anonymous visitors to log in or register on a members-only evening', () => {
    renderPanel(makeEvent({ state: 'members_only', can_rsvp: false, reason: 'members_only' }, { audience: 'members' }), null)
    expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/account/login?next=%2Fevents%2Ffriday-social')
    expect(screen.getByRole('link', { name: 'Join to RSVP' })).toHaveAttribute('href', '/membership')
  })

  it('shows going with calendar download that defaults to discreet', async () => {
    renderPanel(makeEvent({ state: 'going', mine: { status: 'going', party_size: 1, note_to_hosts: '' } }))
    expect(screen.getByText(/You are going/)).toBeInTheDocument()
    const link = screen.getByRole('link', { name: 'Add to calendar' })
    expect(link).toHaveAttribute('href', '/api/events/friday-social/calendar.ics')
    await userEvent.click(screen.getByLabelText(/Include the event name and address/))
    expect(link).toHaveAttribute('href', '/api/events/friday-social/calendar.ics?details=1')
  })

  it('confirms before cancelling and reports the new state', async () => {
    const reopened = rsvpState()
    apiMock.cancelRSVP.mockResolvedValue({ rsvp: reopened })
    const { onChange } = renderPanel(
      makeEvent({ state: 'going', mine: { status: 'going', party_size: 1, note_to_hosts: '' } }),
    )
    await userEvent.click(screen.getByRole('button', { name: 'Change or cancel' }))
    await userEvent.click(screen.getByRole('button', { name: 'Cancel my RSVP' }))
    expect(apiMock.cancelRSVP).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Yes, cancel' }))
    expect(apiMock.cancelRSVP).toHaveBeenCalledWith('friday-social')
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(reopened))
  })

  it('shows the waitlisted state without a calendar link', () => {
    renderPanel(makeEvent({ state: 'waitlisted', mine: { status: 'waitlist', party_size: 1, note_to_hosts: '' } }))
    expect(screen.getByText(/You are on the waitlist/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Add to calendar' })).not.toBeInTheDocument()
  })

  it('shows the count only when the event shares it', () => {
    renderPanel(makeEvent({}, { attendee_count: 12 }))
    expect(screen.getByText('12 going')).toBeInTheDocument()
  })

  it('validates the note length inline', () => {
    renderPanel(makeEvent())
    fireEvent.click(screen.getByRole('button', { name: 'Add a note for the hosts' }))
    const note = screen.getByLabelText(/Note to hosts/)
    expect(note).toHaveAttribute('maxLength', '280')
    fireEvent.change(note, { target: { value: 'x'.repeat(10) } })
    expect(screen.getByText('10 / 280')).toBeInTheDocument()
  })

  it('explains an event the membership does not include, with a way to upgrade', () => {
    renderPanel(makeEvent({ state: 'tier_event_not_included', can_rsvp: false, reason: 'tier_event_not_included' }))
    expect(screen.getByText('Not on your plan')).toBeInTheDocument()
    expect(screen.getByText(/not part of your membership/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'See plans that include it' })).toHaveAttribute('href', '/membership')
    expect(screen.queryByRole('form', { name: 'RSVP' })).not.toBeInTheDocument()
  })

  it('explains a used-up month, with a way to upgrade', () => {
    renderPanel(makeEvent({ state: 'monthly_limit_reached', can_rsvp: false, reason: 'monthly_limit_reached', events_remaining: 0 }))
    expect(screen.getByText('Monthly limit reached')).toBeInTheDocument()
    expect(screen.getByText(/used this month.s events on your membership/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'See plans with more events' })).toHaveAttribute('href', '/membership')
  })

  it('caps the party at what the membership includes and says so', async () => {
    renderPanel(makeEvent({ max_party_size: 2, plan_party_limit: 1, events_remaining: 1 }))
    expect(screen.queryByRole('button', { name: 'One more' })).not.toBeInTheDocument()
    expect(screen.getByText(/Your membership does not include guests here/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'See plans with guests' })).toHaveAttribute('href', '/membership')
    expect(screen.getByText(/This uses your last event this month/)).toBeInTheDocument()
  })

  it('shows the error the server gives when the plan refuses a party size', async () => {
    apiMock.rsvp.mockRejectedValue(new Error('Your membership does not include that many guests here.'))
    renderPanel(makeEvent({ max_party_size: 2, plan_party_limit: 2 }))
    const form = screen.getByRole('form', { name: 'RSVP' })
    await userEvent.click(within(form).getByRole('button', { name: 'One more' }))
    await userEvent.click(within(form).getByRole('button', { name: 'RSVP for 2' }))
    expect(await screen.findByText('Your membership does not include that many guests here.')).toBeInTheDocument()
  })
})

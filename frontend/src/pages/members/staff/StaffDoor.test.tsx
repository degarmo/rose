import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Sidebar, TabBar } from '@/components/members/app/Nav'
import type { Account } from '@/lib/api'
import { landingAfterLogin } from '@/lib/memberApp'
import type { DoorCard, DoorSearch, StaffSession } from '@/lib/safetyApi'
import { renderWithProviders, verifiedUser } from '@/test/render'
import { StaffDoorPage } from './StaffDoorPage'

const door = vi.hoisted(() => ({ search: vi.fn(), act: vi.fn() }))

vi.mock('@/lib/safetyApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/safetyApi')>()
  return { ...actual, doorApi: door }
})

const VOLUNTEER: StaffSession = {
  role: null,
  door_desk: true,
  verified: true,
  verify_url: null,
  needs_enrollment: false,
  admin_url: '/admin/',
  door_desk_url: '/admin/memberships/membership/door-desk/',
}

function as(staff: Partial<StaffSession> | null): Account {
  return { ...verifiedUser, feed_access: false, member_app: null, staff: staff && { ...VOLUNTEER, ...staff } }
}

function card(overrides: Partial<DoorCard> = {}): DoorCard {
  return {
    id: 4,
    reference_code: 'UX3-D3X',
    display_name: 'silver_orchid',
    tier: { name: 'Rose', price: '30.00', currency: 'USD', interval: 'Monthly', guests_included: 1, guest_discount: false, is_free: false },
    status: 'active',
    status_label: 'Active',
    source_label: 'Door desk',
    is_guest_pass: false,
    id_checked: true,
    paid_awaiting_id_check: false,
    period_end: '2026-11-18T12:00:00Z',
    events_remaining: 3,
    do_not_admit: false,
    events_suspended_until: null,
    default_amount: '30.00',
    actions: ['walk_in', 'renew', 'suspend'],
    payments: [{ id: 9, date: '2026-10-18T12:00:00Z', status: 'succeeded', status_label: 'Succeeded', method_label: 'Cash', amount: '30.00', refundable: true }],
    ...overrides,
  }
}

function found(cards: DoorCard[], overrides: Partial<DoorSearch> = {}): DoorSearch {
  return {
    query: 'UX3-D3X',
    results: cards,
    tonight_events: [{ id: 12, title: 'Member Night', starts_at: '2026-10-19T19:30:00-05:00' }],
    donation_methods: [
      { value: 'cash', label: 'Cash' },
      { value: 'card_in_person', label: 'Card in person' },
      { value: 'check', label: 'Check' },
    ],
    join_url: null,
    join_qr: null,
    ...overrides,
  }
}

async function searchFor(code: string) {
  const form = screen.getByRole('search')
  await userEvent.type(within(form).getByLabelText('Reference code or display name'), code)
  await userEvent.click(within(form).getByRole('button', { name: 'Search' }))
}

beforeEach(() => {
  door.search.mockReset()
  door.act.mockReset()
})

describe('the door desk', () => {
  it('is a 404 without the door desk permission, and asks for the two-step login first', () => {
    const { unmount } = renderWithProviders(<StaffDoorPage />, { user: as({ role: 'moderator', door_desk: false }) })
    expect(screen.getByRole('heading', { name: 'This room is not on the map.' })).toBeInTheDocument()
    unmount()
    renderWithProviders(<StaffDoorPage />, { user: as({ verified: false, verify_url: '/admin/login/?next=door' }) })
    expect(screen.getByRole('link', { name: 'Continue' })).toHaveAttribute('href', '/admin/login/?next=door')
    expect(door.search).not.toHaveBeenCalled()
  })

  it('shows a volunteer only the door desk tab', () => {
    renderWithProviders(<StaffDoorPage />, { user: as({}), path: '/members/staff/door' })
    const tabs = within(screen.getByRole('navigation', { name: 'Staff' })).getAllByRole('link')
    expect(tabs.map((tab) => tab.textContent)).toEqual(['Door desk'])
    expect(screen.getByText('Staff · Door desk')).toBeInTheDocument()
  })

  it('finds someone and shows what the door needs to know', async () => {
    door.search.mockResolvedValue(found([card()]))
    renderWithProviders(<StaffDoorPage />, { user: as({}) })
    await searchFor('UX3-D3X')
    const result = await screen.findByRole('article', { name: 'silver_orchid' })
    expect(door.search).toHaveBeenCalledWith('UX3-D3X')
    expect(within(result).getByText('ID verified')).toBeInTheDocument()
    expect(within(result).getByText('3 left')).toBeInTheDocument()
    expect(within(result).getByText('1 per event')).toBeInTheDocument()
    expect(within(result).getByRole('button', { name: 'Check in' })).toBeEnabled()
    expect(within(result).getByRole('button', { name: 'Renew' })).toBeInTheDocument()
    expect(within(result).getByRole('button', { name: 'Suspend' })).toBeInTheDocument()
  })

  it('says "Do not admit" and offers no actions for a barred person', async () => {
    door.search.mockResolvedValue(found([card({ do_not_admit: true, id_checked: false })]))
    renderWithProviders(<StaffDoorPage />, { user: as({}) })
    await searchFor('UX3-D3X')
    const result = await screen.findByRole('article', { name: 'silver_orchid' })
    expect(within(result).getByRole('alert')).toHaveTextContent('Do not admit')
    expect(within(result).getByText('ID check needed')).toBeInTheDocument()
    expect(within(result).queryByRole('button', { name: 'Check in' })).not.toBeInTheDocument()
  })

  it('checks someone in to tonight’s event', async () => {
    door.search.mockResolvedValue(found([card()]))
    door.act.mockResolvedValue({ message: 'UX3-D3X is checked in.' })
    renderWithProviders(<StaffDoorPage />, { user: as({}) })
    await searchFor('UX3-D3X')
    await userEvent.click(await screen.findByRole('button', { name: 'Check in' }))
    const dialog = screen.getByRole('dialog', { name: 'Check in tonight' })
    await userEvent.selectOptions(within(dialog).getByLabelText(/^Party/), '2')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Check in' }))
    await waitFor(() => expect(door.act).toHaveBeenCalledWith({ action: 'walk_in', membership: 4, event: 12, party_size: 2 }))
    expect(await screen.findByText('UX3-D3X is checked in.')).toBeInTheDocument()
    expect(door.search).toHaveBeenCalledTimes(2)
  })

  it('cannot check in without a members-only event tonight', async () => {
    door.search.mockResolvedValue(found([card()], { tonight_events: [] }))
    renderWithProviders(<StaffDoorPage />, { user: as({}) })
    await searchFor('UX3-D3X')
    expect(await screen.findByRole('button', { name: 'No members-only event tonight' })).toBeDisabled()
  })

  it('needs the photo ID box before a first activation, and sends the payment', async () => {
    const waiting = card({ status: 'pending_payment', status_label: 'Pending payment', id_checked: false, actions: ['activate', 'comp'], payments: [] })
    door.search.mockResolvedValue(found([waiting]))
    door.act.mockResolvedValue({ message: 'UX3-D3X is active.' })
    renderWithProviders(<StaffDoorPage />, { user: as({}) })
    await searchFor('UX3-D3X')
    await userEvent.click(await screen.findByRole('button', { name: 'Record payment and activate' }))
    const dialog = screen.getByRole('dialog', { name: 'Record payment and activate' })
    const submit = within(dialog).getByRole('button', { name: 'Record payment and activate' })
    expect(submit).toBeDisabled()
    expect(within(dialog).getByLabelText(/^Amount/)).toHaveValue('30.00')
    await userEvent.click(within(dialog).getByRole('checkbox', { name: /Photo ID checked, 18\+/ }))
    await userEvent.click(submit)
    await waitFor(() =>
      expect(door.act).toHaveBeenCalledWith({ action: 'activate', membership: 4, method: 'cash', amount: '30.00', note: '', id_checked: true }),
    )
  })

  it('shows the refusal from the server in the dialog', async () => {
    const { ApiError } = await import('@/lib/api')
    door.search.mockResolvedValue(found([card()]))
    door.act.mockRejectedValue(new ApiError(400, 'Enter a reason.'))
    renderWithProviders(<StaffDoorPage />, { user: as({}) })
    await searchFor('UX3-D3X')
    await userEvent.click(await screen.findByRole('button', { name: 'Suspend' }))
    const dialog = screen.getByRole('dialog', { name: 'Suspend' })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Suspend' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Enter a reason.')
  })

  it('reveals the signature name only when asked, and says it was logged', async () => {
    door.search.mockResolvedValue(found([card()]))
    door.act.mockResolvedValue({ signature: { membership: 4, name: 'Morgan Legalname' } })
    renderWithProviders(<StaffDoorPage />, { user: as({}) })
    await searchFor('UX3-D3X')
    expect(screen.queryByText('Morgan Legalname')).not.toBeInTheDocument()
    await userEvent.click(await screen.findByRole('button', { name: 'Show signature name' }))
    expect(await screen.findByText('Morgan Legalname')).toBeInTheDocument()
    expect(screen.getByText('(this view was logged)')).toBeInTheDocument()
    expect(door.act).toHaveBeenCalledWith({ action: 'show_signature', membership: 4 })
  })

  it('says when nothing is found', async () => {
    door.search.mockResolvedValue(found([], { query: 'nobody' }))
    renderWithProviders(<StaffDoorPage />, { user: as({}) })
    await searchFor('nobody')
    expect(await screen.findByText('Nothing found for “nobody”')).toBeInTheDocument()
  })
})

/** The sidebar's links by their titles (each label is there twice: shown and for screen readers). */
function titles(nav: HTMLElement) {
  return within(nav)
    .getAllByRole('link')
    .map((link) => link.getAttribute('title'))
    .filter((title): title is string => Boolean(title))
}

describe('getting to the door desk', () => {
  it('lands a volunteer on the door desk after logging in', () => {
    expect(landingAfterLogin({ member_app: null, staff: VOLUNTEER }, null, '/members/home')).toBe('/members/staff/door')
    expect(landingAfterLogin({ member_app: null, staff: VOLUNTEER }, '/events/x', '/events/x')).toBe('/events/x')
  })

  it('puts the door desk first in a volunteer’s sidebar and tab bar, loading the page afresh', () => {
    renderWithProviders(
      <>
        <Sidebar me={null} panel={null} onPanel={() => undefined} onCreate={() => undefined} />
        <TabBar me={null} onCreate={() => undefined} />
      </>,
      { user: as({}), path: '/members/home' },
    )
    const [sidebar, tabBar] = screen.getAllByRole('navigation', { name: 'Members' })
    const items = titles(sidebar)
    expect(items.slice(0, 3)).toEqual(['Door desk', 'Home', 'Settings'])
    expect(items).not.toContain('Staff')
    expect(within(sidebar).getByTitle('Door desk')).toHaveAttribute('href', '/members/staff/door')
    expect(within(tabBar).getAllByRole('link')[0]).toHaveAccessibleName('Door desk')
    expect(within(tabBar).queryByRole('link', { name: 'Staff' })).not.toBeInTheDocument()
  })

  it('shows the team the door desk beside Staff, and no door desk without the permission', () => {
    const { unmount } = renderWithProviders(<Sidebar me={null} panel={null} onPanel={() => undefined} onCreate={() => undefined} />, {
      user: as({ role: 'admin' }),
      path: '/members/home',
    })
    const names = titles(screen.getByRole('navigation', { name: 'Members' }))
    expect(names.slice(names.indexOf('Staff'), names.indexOf('Staff') + 2)).toEqual(['Staff', 'Door desk'])
    unmount()
    renderWithProviders(<Sidebar me={null} panel={null} onPanel={() => undefined} onCreate={() => undefined} />, {
      user: as({ role: 'moderator', door_desk: false }),
      path: '/members/home',
    })
    const moderator = titles(screen.getByRole('navigation', { name: 'Members' }))
    expect(moderator).toContain('Staff')
    expect(moderator).not.toContain('Door desk')
  })
})

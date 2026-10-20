import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Sidebar, TabBar } from '@/components/members/app/Nav'
import type { Account } from '@/lib/api'
import { landingAfterLogin } from '@/lib/memberApp'
import type { DoorCard, DoorPerson, DoorSearch, StaffSession } from '@/lib/safetyApi'
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
  admin_url: '/admin/', age_check_required: true, can_change_age_check: false, age_check_url: 'https://site.example/admin/pages/sitesettings/age-verification/',
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
    team_account: false,
    is_you: false,
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
    needs_id: false,
    results: cards,
    people: [],
    witnesses: [],
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

function person(overrides: Partial<DoorPerson> = {}): DoorPerson {
  return { id: 31, display_name: 'quiet_lamp', team_account: false, feed_granted: true, is_you: false, id_checked: false, do_not_admit: false, actions: ['verify'], ...overrides }
}

describe('arriving from the admin', () => {
  it('searches the code in the address, or opens the "Needs ID check" list', async () => {
    door.search.mockResolvedValue(found([card()]))
    const { unmount } = renderWithProviders(<StaffDoorPage />, { user: as({}), path: '/members/staff/door?q=UX3-D3X' })
    expect(await screen.findByRole('article', { name: 'silver_orchid' })).toBeInTheDocument()
    expect(door.search).toHaveBeenCalledWith('UX3-D3X')
    unmount()
    door.search.mockResolvedValue(found([], { needs_id: true, query: '' }))
    renderWithProviders(<StaffDoorPage />, { user: as({}), path: '/members/staff/door?needs_id=1' })
    expect(await screen.findByRole('heading', { name: 'Waiting for an ID check' })).toBeInTheDocument()
    expect(door.search).toHaveBeenLastCalledWith('', true)
  })
})

describe('ID checks at the door desk', () => {
  it('lists everyone waiting for an ID check, people without a membership included', async () => {
    door.search.mockResolvedValue(found([card({ id_checked: false, actions: ['walk_in', 'verify'] })], { needs_id: true, query: '', people: [person()] }))
    renderWithProviders(<StaffDoorPage />, { user: as({}) })
    await userEvent.click(screen.getByRole('button', { name: 'Needs ID check' }))
    expect(screen.getByRole('button', { name: 'Needs ID check' })).toHaveAttribute('aria-pressed', 'true')
    await waitFor(() => expect(door.search).toHaveBeenCalledWith('', true))
    expect(await screen.findByRole('heading', { name: 'Waiting for an ID check' })).toBeInTheDocument()
    const granted = screen.getByRole('article', { name: 'quiet_lamp' })
    expect(within(granted).getByText('Granted, awaiting ID check')).toBeInTheDocument()
    expect(within(granted).getByText('ID check needed')).toBeInTheDocument()
  })

  it('records an ID check for an account with no membership, and nothing else', async () => {
    door.search.mockResolvedValue(found([], { query: 'quiet', people: [person()] }))
    door.act.mockResolvedValue({ message: 'quiet_lamp: ID check recorded.' })
    renderWithProviders(<StaffDoorPage />, { user: as({}) })
    await searchFor('quiet')
    await userEvent.click(within(await screen.findByRole('article', { name: 'quiet_lamp' })).getByRole('button', { name: 'Record ID check' }))
    const dialog = screen.getByRole('dialog', { name: 'Record ID check' })
    expect(within(dialog).getByRole('button', { name: 'Record ID check' })).toBeDisabled()
    await userEvent.click(within(dialog).getByRole('checkbox', { name: /Photo ID checked, 18\+/ }))
    await userEvent.click(within(dialog).getByRole('button', { name: 'Record ID check' }))
    await waitFor(() => expect(door.act).toHaveBeenCalledWith({ action: 'verify', person: 31, id_checked: true }))
  })

  it('needs a witness for your own ID check', async () => {
    door.search.mockResolvedValue(found([], { query: 'me', people: [person({ id: 7, display_name: 'desk_me', team_account: true, feed_granted: false, is_you: true })], witnesses: [{ id: 8, display_name: 'team_staff' }] }))
    door.act.mockResolvedValue({ message: 'desk_me: ID check recorded.' })
    renderWithProviders(<StaffDoorPage />, { user: as({}) })
    await searchFor('me')
    await userEvent.click(within(await screen.findByRole('article', { name: /desk_me/ })).getByRole('button', { name: 'Record ID check' }))
    const dialog = screen.getByRole('dialog', { name: 'Record ID check' })
    await userEvent.click(within(dialog).getByRole('checkbox', { name: /Photo ID checked, 18\+/ }))
    expect(within(dialog).getByRole('button', { name: 'Record ID check' })).toBeDisabled()
    await userEvent.selectOptions(within(dialog).getByLabelText(/^Witness/), '8')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Record ID check' }))
    await waitFor(() => expect(door.act).toHaveBeenCalledWith({ action: 'verify', person: 7, witness: 8, id_checked: true }))
  })

  it('revokes a check with a reason', async () => {
    door.search.mockResolvedValue(found([card({ actions: ['walk_in', 'renew', 'suspend', 'revoke'] })]))
    door.act.mockResolvedValue({ message: 'silver_orchid: ID check revoked.' })
    renderWithProviders(<StaffDoorPage />, { user: as({}) })
    await searchFor('UX3-D3X')
    await userEvent.click(await screen.findByRole('button', { name: 'Revoke ID check' }))
    const dialog = screen.getByRole('dialog', { name: 'Revoke the ID check' })
    expect(within(dialog).getByText(/member feed closes for them at once/)).toBeInTheDocument()
    await userEvent.type(within(dialog).getByLabelText(/^Reason/), 'Checked the wrong person')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Revoke' }))
    await waitFor(() => expect(door.act).toHaveBeenCalledWith({ action: 'revoke', membership: 4, reason: 'Checked the wrong person' }))
  })

  it('asks for the ID box before renewing someone with no check on file', async () => {
    door.search.mockResolvedValue(found([card({ status: 'expired', status_label: 'Expired', id_checked: false, actions: ['renew', 'verify'] })]))
    renderWithProviders(<StaffDoorPage />, { user: as({}) })
    await searchFor('UX3-D3X')
    await userEvent.click(await screen.findByRole('button', { name: 'Renew' }))
    const dialog = screen.getByRole('dialog', { name: 'Renew' })
    expect(within(dialog).getByRole('checkbox', { name: /Photo ID checked, 18\+/ })).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Renew' })).toBeDisabled()
  })
})

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

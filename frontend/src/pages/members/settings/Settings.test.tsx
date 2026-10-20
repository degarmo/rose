import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthContext, type AuthState } from '@/components/layout/authContext'
import { MembersTestProvider } from '@/test/MembersTestProvider'
import { ToastProvider } from '@/components/ui'
import type { Account, Preferences } from '@/lib/api'
import type { FeedAccount, FeedPath, FeedTeaser, PathStep } from '@/lib/membersApi'
import type { MemberActionData } from '@/lib/safetyApi'
import { me } from '@/test/members'
import { makeMembership } from '@/test/membership'
import { verifiedUser } from '@/test/render'
import { HomePage } from '../HomePage'
import { JoinFeedPage } from '../JoinFeedPage'
import { SettingsPage } from './SettingsPage'

const account = vi.hoisted(() => ({
  myRSVPs: vi.fn(),
  events: vi.fn(),
  preferences: vi.fn(),
  updatePreferences: vi.fn(),
  twoStep: vi.fn(),
  startTwoStep: vi.fn(),
  confirmTwoStep: vi.fn(),
  disableTwoStep: vi.fn(),
  sessions: vi.fn(),
  signOutEverywhere: vi.fn(),
  dataExport: vi.fn(),
  requestDataExport: vi.fn(),
}))
const membership = vi.hoisted(() => ({
  me: vi.fn(),
  cancel: vi.fn(),
  setAutoRenew: vi.fn(),
}))
const safety = vi.hoisted(() => ({
  notices: vi.fn(),
  markNoticesSeen: vi.fn(),
  myReports: vi.fn(),
  appeal: vi.fn(),
}))
const feed = vi.hoisted(() => ({
  get: vi.fn(),
  path: vi.fn(),
  teaser: vi.fn(),
  acceptGuidelines: vi.fn(),
  stepAway: vi.fn(),
  erase: vi.fn(),
}))
const membersApi = vi.hoisted(() => ({
  myBlocks: vi.fn(),
  myMutes: vi.fn(),
  updateMe: vi.fn(),
  unrelate: vi.fn(),
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return { ...actual, api: { ...actual.api, ...account } }
})
vi.mock('@/lib/membershipApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membershipApi')>()
  return {
    ...actual,
    membershipApi: { ...actual.membershipApi, ...membership },
  }
})
vi.mock('@/lib/safetyApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/safetyApi')>()
  return { ...actual, safetyApi: { ...actual.safetyApi, ...safety } }
})
vi.mock('@/lib/membersApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membersApi')>()
  return {
    ...actual,
    feedAccount: { ...actual.feedAccount, ...feed },
    members: { ...actual.members, ...membersApi },
  }
})

const preferences: Preferences = {
  pronouns: '',
  calendar_details: false,
  email_event_reminders: true,
  email_membership_reminders: true,
  notify_likes: true,
  notify_comments: true,
  discreet_subjects: true,
}

const active = makeMembership({
  status: 'active',
  status_label: 'Active',
  current_period_start: '2026-10-13T12:00:00Z',
  current_period_end: '2026-11-12T12:00:00Z',
  code_expires_at: null,
  id_checked: true,
  events_remaining_this_month: 3,
  payments: [
    {
      id: 41,
      created_at: '2026-10-13T12:00:00Z',
      amount_cents: 2500,
      method: 'cash',
      method_label: 'Cash',
      status: 'succeeded',
      status_label: 'Succeeded',
    },
    {
      id: 40,
      created_at: '2026-09-02T12:00:00Z',
      amount_cents: 2500,
      method: 'online',
      method_label: 'Online',
      status: 'failed',
      status_label: 'Failed',
    },
  ],
})

const suspension: MemberActionData = {
  id: 3,
  kind: 'feed_suspension',
  kind_label: 'Feed suspension',
  rule: 'Consent first',
  reason: 'A photo was posted without asking.',
  created_at: '2026-10-19T12:00:00Z',
  ends_at: '2026-10-26T12:00:00Z',
  in_force: true,
  reversed_at: null,
  reversal_reason: '',
  appeal: null,
}

function feedAccountFor(overrides: Partial<FeedAccount>): FeedAccount {
  return {
    participating: true,
    can_join: true,
    awaiting_age_check: false,
    can_view: true,
    banned: false,
    suspended_until: null,
    accepted_current_guidelines: true,
    guidelines: {
      version: 4,
      title: 'Community guidelines',
      body: 'Be kind.',
      body_html: '<p>Be kind.</p>',
      published_at: '2026-09-01T12:00:00Z',
    },
    guidelines_accepted_at: '2026-09-03T12:00:00Z',
    has_content: true,
    profile: {
      display_name: 'night_owl',
      bio: '',
      hide_from_directory: true,
      has_avatar: false,
    },
    ...overrides,
  }
}

const ORDER: PathStep['key'][] = ['email', 'plan', 'door', 'age', 'join']

/** Home's checklist with every step before `at` done, `at` current and the rest to come. */
function pathAt(at: PathStep['key'] | 'complete', changes: Partial<Record<PathStep['key'], object>> = {}): FeedPath {
  const reached = at === 'complete' ? ORDER.length : ORDER.indexOf(at)
  const state = (key: PathStep['key']) => {
    const index = ORDER.indexOf(key)
    return index < reached ? 'done' : index === reached ? 'current' : 'upcoming'
  }
  const steps = [
    { key: 'email', state: state('email') },
    { key: 'plan', state: state('plan'), included: false, tier: null },
    { key: 'door', state: state('door'), included: false, reference_code: null, waiting_for: null },
    { key: 'age', state: state('age'), notice: false },
    { key: 'join', state: state('join'), paused: false, can_join: at === 'join', early: false },
  ].map((step) => ({ ...step, ...changes[step.key as PathStep['key']] })) as PathStep[]
  return { steps, complete: at === 'complete' }
}

const noTeaser: FeedTeaser = { tiles: [], post: null }

function Where() {
  const location = useLocation()
  return <p data-testid="where">{location.pathname + location.hash}</p>
}

function renderSettings(path: string, { user = verifiedUser as Account, inFeed = false, refresh = async () => undefined } = {}) {
  const auth: AuthState = {
    status: 'ready',
    user,
    applySession: vi.fn(),
    refresh,
    logout: vi.fn(async () => undefined),
  }
  const routes = (
    <Routes>
      <Route path="/members/home" element={<HomePage />} />
      <Route path="/members/join-feed" element={<JoinFeedPage />} />
      <Route path="/members/settings" element={<SettingsPage />} />
      <Route path="/members/settings/:section" element={<SettingsPage />} />
      <Route path="*" element={<p>Elsewhere</p>} />
    </Routes>
  )
  render(
    <MemoryRouter initialEntries={[path]}>
      <AuthContext.Provider value={auth}>
        <ToastProvider>
          {inFeed ? (
            <MembersTestProvider me={me} openPost={vi.fn()}>
              {routes}
            </MembersTestProvider>
          ) : (
            routes
          )}
          <Where />
        </ToastProvider>
      </AuthContext.Provider>
    </MemoryRouter>,
  )
  return auth
}

beforeEach(() => {
  for (const group of [account, membership, safety, feed, membersApi]) Object.values(group).forEach((fn) => fn.mockReset())
  account.myRSVPs.mockResolvedValue([])
  account.events.mockResolvedValue([])
  account.preferences.mockResolvedValue(preferences)
  account.updatePreferences.mockImplementation(async (changes: Partial<Preferences>) => ({ ...preferences, ...changes }))
  account.dataExport.mockResolvedValue({ export: null })
  account.twoStep.mockResolvedValue({
    enabled: false,
    backup_codes_left: 0,
    required: false,
  })
  account.sessions.mockResolvedValue([])
  membership.me.mockResolvedValue({ membership: null, entitlements: [] })
  safety.notices.mockResolvedValue([])
  safety.myReports.mockResolvedValue([])
  feed.get.mockResolvedValue(feedAccountFor({}))
  feed.path.mockResolvedValue(pathAt('plan'))
  feed.teaser.mockResolvedValue(noTeaser)
  membersApi.myBlocks.mockResolvedValue({ blocked: [] })
  membersApi.myMutes.mockResolvedValue({ muted: [] })
})

describe('Settings layout', () => {
  it('lists every section, Report a concern and Log out', async () => {
    renderSettings('/members/settings')
    const nav = screen.getByRole('navigation', { name: 'Settings' })
    for (const label of ['Membership', 'Profile', 'Privacy', 'Notifications', 'Security', 'Notices', 'Community guidelines', 'Leave the community']) {
      expect(within(nav).getByRole('link', { name: new RegExp(`^${label}`) })).toBeInTheDocument()
    }
    expect(within(nav).getByRole('link', { name: 'Report a concern' })).toHaveAttribute('href', '/members/report')
    expect(within(nav).getByRole('button', { name: 'Log out' })).toBeInTheDocument()
    expect(within(nav).queryByRole('link', { name: /^Staff/ })).not.toBeInTheDocument()
    expect(await screen.findByText("You don't have a membership yet")).toBeInTheDocument()
  })

  it.each([
    ['#password', '/members/settings/security'],
    ['#sessions', '/members/settings/security'],
    ['#membership', '/members/settings/membership'],
    ['#rsvps', '/members/settings/membership'],
    ['#appearance', '/members/settings/profile'],
    ['#safety', '/members/settings/notices'],
    ['#delete', '/members/settings/leave'],
  ])('sends the old anchor %s to its section', async (hash, to) => {
    renderSettings(`/members/settings${hash}`)
    await waitFor(() => expect(screen.getByTestId('where')).toHaveTextContent(to))
  })

  it('answers an unknown section with the 404', () => {
    renderSettings('/members/settings/nowhere')
    expect(screen.getByRole('heading', { name: 'This room is not on the map.' })).toBeInTheDocument()
  })

  it('asks an unconfirmed account to confirm its email', () => {
    renderSettings('/members/settings/profile', {
      user: { ...verifiedUser, email_verified: false },
    })
    expect(screen.getByRole('button', { name: 'Send a new link' })).toBeInTheDocument()
  })
})

describe('Settings · Membership', () => {
  it('shows the card with the door code, Change plan and Cancel, and dated payments with receipts', async () => {
    membership.me.mockResolvedValue({
      membership: active,
      entitlements: ['members_events'],
    })
    renderSettings('/members/settings/membership', {
      user: { ...verifiedUser, has_membership: true },
    })
    expect(await screen.findByText('Paid through November 12, 2026')).toBeInTheDocument()
    expect(screen.getByText('3 events left this month')).toBeInTheDocument()
    expect(screen.getByText('R7K-42Q')).toBeInTheDocument()
    expect(await screen.findByAltText('QR code for R7K-42Q')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Change plan' })).toHaveAttribute('href', '/membership')
    const receipts = screen.getAllByRole('link', { name: 'Receipt' })
    expect(receipts).toHaveLength(1)
    expect(receipts[0]).toHaveAttribute('href', '/members/settings/membership/receipts/41')
    expect(screen.getByText('Did not go through')).toBeInTheDocument()
    expect(screen.queryByText('Cash')).not.toBeInTheDocument() // dates and amounts only
    expect(screen.queryByRole('switch')).not.toBeInTheDocument() // in person: no auto-renew
  })

  it('confirms before cancelling', async () => {
    membership.me.mockResolvedValue({ membership: active, entitlements: [] })
    membership.cancel.mockResolvedValue({
      membership: { ...active, cancel_at_period_end: true },
      entitlements: [],
    })
    renderSettings('/members/settings/membership')
    await userEvent.click(await screen.findByRole('button', { name: 'Cancel' }))
    const dialog = screen.getByRole('dialog', {
      name: 'Cancel your membership?',
      hidden: true,
    })
    expect(within(dialog).getByText(/You keep access until November 12, 2026/)).toBeInTheDocument()
    expect(membership.cancel).not.toHaveBeenCalled()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Cancel at period end' }))
    await waitFor(() => expect(membership.cancel).toHaveBeenCalledOnce())
    expect(await screen.findByText('Expires November 12, 2026. It will not renew.')).toBeInTheDocument()
  })

  it('lets online members turn automatic renewal off', async () => {
    const online = {
      ...active,
      source: 'provider' as const,
      online: true,
      auto_renew: true,
    }
    membership.me.mockResolvedValue({ membership: online, entitlements: [] })
    membership.setAutoRenew.mockResolvedValue({
      membership: { ...online, auto_renew: false, cancel_at_period_end: true },
      entitlements: [],
    })
    renderSettings('/members/settings/membership')
    const toggle = await screen.findByRole('switch', {
      name: /Renew automatically/,
    })
    expect(screen.getByText('Renews November 12, 2026')).toBeInTheDocument()
    await userEvent.click(toggle)
    await waitFor(() => expect(membership.setAutoRenew).toHaveBeenCalledWith(false))
    expect(await screen.findByText('Expires November 12, 2026. It will not renew.')).toBeInTheDocument()
  })

  it('shows a pending code with what to bring', async () => {
    membership.me.mockResolvedValue({
      membership: makeMembership(),
      entitlements: [],
    })
    renderSettings('/members/settings/membership')
    expect(await screen.findByText('Waiting for payment')).toBeInTheDocument()
    expect(screen.getByText(/Your payment: \$25 a month/)).toBeInTheDocument()
    expect(screen.getByText(/stays open until November 17, 2026/)).toBeInTheDocument()
    expect(screen.getByText('No payments yet')).toBeInTheDocument()
  })

  it('offers to join again after expiry, without a code', async () => {
    membership.me.mockResolvedValue({
      membership: { ...active, status: 'expired', status_label: 'Expired' },
      entitlements: [],
    })
    renderSettings('/members/settings/membership')
    expect(await screen.findByText('Ended November 12, 2026')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Join again' })).toHaveAttribute('href', '/membership')
    expect(screen.queryByText('R7K-42Q')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cancel' })).not.toBeInTheDocument()
  })

  it('lists upcoming plans with their status', async () => {
    account.myRSVPs.mockResolvedValue([
      {
        status: 'waitlist',
        party_size: 2,
        note_to_hosts: '',
        event: {
          slug: 'late',
          title: 'Late lounge',
          starts_at: '2026-10-23T02:00:00Z',
          ends_at: '2026-10-23T05:00:00Z',
          timing: 'upcoming',
          location_label: '',
        },
      },
    ])
    renderSettings('/members/settings/membership')
    expect(await screen.findByRole('link', { name: 'Late lounge' })).toHaveAttribute('href', '/events/late')
    expect(screen.getByText('On the waitlist')).toBeInTheDocument()
    expect(screen.getByText(/Party of 2/)).toBeInTheDocument()
  })

  it('shows an error with retry', async () => {
    membership.me.mockRejectedValueOnce(new Error('offline'))
    renderSettings('/members/settings/membership')
    await userEvent.click(await screen.findByRole('button', { name: 'Try again' }))
    expect(await screen.findByText("You don't have a membership yet")).toBeInTheDocument()
  })
})

describe('Settings · Notifications', () => {
  it('saves email switches and keeps discreet subject lines locked on', async () => {
    renderSettings('/members/settings/notifications')
    const reminders = await screen.findByRole('switch', {
      name: /Event reminders/,
    })
    await userEvent.click(reminders)
    await waitFor(() =>
      expect(account.updatePreferences).toHaveBeenCalledWith({
        email_event_reminders: false,
      }),
    )
    const discreet = screen.getByRole('switch', {
      name: /Discreet subject lines/,
    })
    expect(discreet).toBeChecked()
    expect(discreet).toBeDisabled()
    // Without the feed there are no in-app switches, only the way to it.
    expect(screen.queryByRole('switch', { name: /Likes/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'See plans with the feed' })).toHaveAttribute('href', '/membership')
  })

  it('has in-app switches for feed members', async () => {
    renderSettings('/members/settings/notifications', {
      user: { ...verifiedUser, feed_access: true, member_app: 'open' },
      inFeed: true,
    })
    await userEvent.click(await screen.findByRole('switch', { name: /Comments/ }))
    await waitFor(() =>
      expect(account.updatePreferences).toHaveBeenCalledWith({
        notify_comments: false,
      }),
    )
  })
})

describe('Settings · Privacy', () => {
  it('shows no feed settings or people without the feed, but the calendar default and the export', async () => {
    renderSettings('/members/settings/privacy')
    expect(await screen.findByText('Feed privacy')).toBeInTheDocument()
    expect(membersApi.myBlocks).not.toHaveBeenCalled()
    expect(feed.get).not.toHaveBeenCalled()
    const calendar = await screen.findByRole('switch', {
      name: /Name the event in calendar files/,
    })
    expect(calendar).not.toBeChecked()
    expect(screen.getByText(/Rose - Evening/)).toBeInTheDocument()
    account.requestDataExport.mockResolvedValue({
      export: { ready: false, expires_at: null },
    })
    await userEvent.click(screen.getByRole('button', { name: /Export my data/ }))
    expect(await screen.findByText('Your copy is being prepared. Watch your inbox.')).toBeInTheDocument()
  })

  it('lists blocked and muted members for feed members, with undo', async () => {
    membersApi.myBlocks.mockResolvedValue({ blocked: ['velvet_hour'] })
    membersApi.myMutes.mockResolvedValue({ muted: ['quiet_hours'] })
    membersApi.unrelate.mockResolvedValue({ ok: true })
    renderSettings('/members/settings/privacy', {
      user: {
        ...verifiedUser,
        feed_access: true,
        member_app: 'open',
        feed_controls: true,
      },
      inFeed: true,
    })
    expect(
      await screen.findByRole('switch', {
        name: /Hide me from the member directory/,
      }),
    ).toBeInTheDocument()
    // Large page: wait on the text, then query by role once.
    await screen.findByText('quiet_hours', { selector: 'span.truncate' })
    expect(screen.getByRole('button', { name: 'Unblock velvet_hour' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Unmute quiet_hours' }))
    await waitFor(() => expect(membersApi.unrelate).toHaveBeenCalledWith('quiet_hours', 'mute'))
  })
})

describe('Settings · Security', () => {
  it('lists where you are signed in and logs out everywhere after confirming', async () => {
    account.sessions.mockResolvedValue([
      {
        device: 'Safari on iPhone',
        signed_in_at: '2026-10-18T12:00:00Z',
        last_seen_at: new Date().toISOString(),
        current: true,
        active_now: true,
      },
      {
        device: 'Firefox on Linux',
        signed_in_at: '2026-10-01T12:00:00Z',
        last_seen_at: '2026-10-02T12:00:00Z',
        current: false,
        active_now: false,
      },
    ])
    account.signOutEverywhere.mockResolvedValue({ user: null, csrfToken: 'x' })
    renderSettings('/members/settings/security')
    expect(await screen.findByText('Safari on iPhone')).toBeInTheDocument()
    expect(screen.getByText('This device')).toBeInTheDocument()
    expect(screen.getByText(/last seen/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Log out everywhere' }))
    const dialog = screen.getByRole('dialog', {
      name: 'Log out everywhere?',
      hidden: true,
    })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Log out everywhere' }))
    await waitFor(() => expect(screen.getByTestId('where')).toHaveTextContent('/account/login'))
  })

  it('sets up two-step login and shows the backup codes once', async () => {
    account.startTwoStep.mockResolvedValue({
      qr: 'data:image/png;base64,AA',
      secret: 'ABCD EFGH',
    })
    account.confirmTwoStep.mockResolvedValue({
      enabled: true,
      backup_codes_left: 10,
      required: false,
      backup_codes: ['11111111', '22222222'],
    })
    renderSettings('/members/settings/security')
    await userEvent.click(await screen.findByRole('button', { name: 'Set up' }))
    await userEvent.type(await screen.findByLabelText(/Six-digit code/), '123456')
    await userEvent.click(screen.getByRole('button', { name: 'Turn on' }))
    await waitFor(() => expect(account.confirmTwoStep).toHaveBeenCalledWith('123456'))
    expect(await screen.findByText('11111111')).toBeInTheDocument()
    expect(screen.getByText('On')).toBeInTheDocument()
  })

  it('keeps two-step login on for staff', async () => {
    account.twoStep.mockResolvedValue({
      enabled: true,
      backup_codes_left: 9,
      required: true,
    })
    renderSettings('/members/settings/security')
    expect(await screen.findByText(/Required for staff accounts/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Turn off' })).not.toBeInTheDocument()
  })
})

describe('Settings · Notices', () => {
  it('shows a decision with its rule and reason, takes one appeal, and the reports sent', async () => {
    safety.notices.mockResolvedValue([suspension])
    safety.myReports.mockResolvedValue([
      {
        id: 9,
        kind_label: 'Post',
        created_at: '2026-10-18T12:00:00Z',
        status: 'reviewed',
      },
    ])
    safety.appeal.mockResolvedValue({
      ...suspension,
      appeal: {
        id: 1,
        status: 'open',
        status_label: 'Open',
        created_at: '2026-10-19T13:00:00Z',
        decided_at: null,
      },
    })
    renderSettings('/members/settings/notices')
    expect(await screen.findByText('Feed suspension')).toBeInTheDocument()
    expect(screen.getByText(/Consent first/)).toBeInTheDocument()
    expect(await screen.findByText('Reviewed')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Appeal this decision' }))
    await userEvent.type(screen.getByLabelText(/Your appeal/), 'I had asked them first.')
    await userEvent.click(screen.getByRole('button', { name: 'Send appeal' }))
    await waitFor(() => expect(safety.appeal).toHaveBeenCalledWith(3, 'I had asked them first.'))
    expect(await screen.findByText(/waiting for review/)).toBeInTheDocument()
  })

  it('badges the row with the unseen count and marks them seen when opened', async () => {
    safety.notices.mockResolvedValue([suspension])
    safety.markNoticesSeen.mockResolvedValue({ unread_notices: 0 })
    const refresh = vi.fn(async () => undefined)
    renderSettings('/members/settings/notices', { user: { ...verifiedUser, unread_notices: 2 }, refresh })
    const row = within(screen.getByRole('navigation', { name: 'Settings' })).getByRole('link', { name: /^Notices/ })
    expect(row).toHaveTextContent('2 unread')
    await waitFor(() => expect(safety.markNoticesSeen).toHaveBeenCalledOnce())
    await waitFor(() => expect(refresh).toHaveBeenCalled())
  })

  it('has no badge and marks nothing when all is seen, and says so when empty', async () => {
    renderSettings('/members/settings/notices')
    expect(await screen.findByText('No notices')).toBeInTheDocument()
    expect(screen.getByText('You’re all good.')).toBeInTheDocument()
    expect(within(screen.getByRole('navigation', { name: 'Settings' })).getByRole('link', { name: /^Notices/ })).not.toHaveTextContent('unread')
    expect(safety.markNoticesSeen).not.toHaveBeenCalled()
  })
})

describe('Settings · Community guidelines', () => {
  it('keeps only the guidelines and Report a concern', async () => {
    renderSettings('/members/settings/guidelines')
    const section = screen.getByRole('region', { name: 'Community guidelines' })
    expect(within(section).getByRole('link', { name: /Report a concern/ })).toHaveAttribute('href', '/members/report')
    expect(screen.queryByText('Notices about your account')).not.toBeInTheDocument()
    expect(screen.queryByText('Reports you sent')).not.toBeInTheDocument()
    expect(safety.notices).not.toHaveBeenCalled()
  })

  it('shows the version and the date a feed member accepted it', async () => {
    renderSettings('/members/settings/guidelines', {
      user: {
        ...verifiedUser,
        feed_controls: true,
        feed_access: true,
        member_app: 'open',
      },
      inFeed: true,
    })
    expect(await screen.findByText(/Version 4/)).toBeInTheDocument()
    expect(screen.getByText('You accepted this version on September 3, 2026.')).toBeInTheDocument()
  })
})

describe('Settings · Leave', () => {
  it('explains what is removed and asks for the password to delete the account', async () => {
    renderSettings('/members/settings/leave')
    expect(screen.getByText(/nothing to erase/)).toBeInTheDocument()
    expect(screen.getByText('Every RSVP (your places go to the waitlist)')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Delete my account' }))
    const dialog = screen.getByRole('dialog', {
      name: 'Delete your account?',
      hidden: true,
    })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Delete for good' }))
    expect(within(dialog).getByText('Enter your password to confirm.')).toBeInTheDocument()
  })
})

describe('Home', () => {
  it('greets the person and invites them to a plan when they have none', async () => {
    renderSettings('/members/home')
    expect(screen.getByRole('heading', { name: 'night_owl' })).toBeInTheDocument()
    expect(await screen.findByText("You don't have a membership yet")).toBeInTheDocument()
    expect(await screen.findByText('Nothing on the calendar yet')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Compare plans' })).toHaveAttribute('href', '/membership')
    expect(screen.getByText('The member community')).toBeInTheDocument()
    expect(screen.getByText('Members share photos, plans and conversation here')).toBeInTheDocument()
    // The membership card's and the preview's.
    for (const link of screen.getAllByRole('link', { name: 'See plans' })) expect(link).toHaveAttribute('href', '/membership')
  })

  it('shows the membership, what it includes, events with RSVP status and the way to join the feed', async () => {
    membership.me.mockResolvedValue({
      membership: active,
      entitlements: ['members_events'],
    })
    account.events.mockResolvedValue([
      {
        id: 1,
        slug: 'thu',
        title: 'Thursday class',
        summary: '',
        category: 'class',
        category_label: 'Class',
        audience: 'members',
        starts_at: '2026-10-23T00:00:00Z',
        ends_at: '2026-10-23T02:00:00Z',
        timing: 'upcoming',
        location_label: '',
        hero_image: null,
        rsvp: { state: 'going' },
        attendee_count: null,
      },
    ])
    feed.path.mockResolvedValue(pathAt('join'))
    renderSettings('/members/home', {
      user: { ...verifiedUser, has_membership: true, member_app: 'join' },
    })
    expect(await screen.findByText('Monthly includes')).toBeInTheDocument()
    expect(screen.getByText('Members-only nights')).toBeInTheDocument()
    expect(await screen.findByText('Going')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Join the community' })).toHaveAttribute('href', '/members/join-feed')
    // A plan with the community is chosen: the preview has no plans button.
    expect(screen.getByText('The member community')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'See plans' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Manage membership' })).toHaveAttribute('href', '/members/settings/membership')
  })
})

describe('the age check', () => {
  const waiting = { ...verifiedUser, has_membership: true, member_app: 'verify' as const, age_check: { verified: false, needed: true, notice: false } }
  const paidWaiting = makeMembership({ reference_code: 'R7K-42Q', paid_awaiting_id_check: true, status_label: 'Waiting for ID check', id_checked: false })

  it('shows the age check on Home as a step: what to bring, the door code once, and that nothing is stored', async () => {
    membership.me.mockResolvedValue({ membership: paidWaiting, entitlements: [] })
    feed.path.mockResolvedValue(pathAt('door', { door: { reference_code: 'R7K-42Q', waiting_for: 'id_check' }, join: { early: true } }))
    renderSettings('/members/home', { user: waiting })
    expect(await screen.findByText(/Bring a valid photo ID showing you are 18 or older/)).toBeInTheDocument()
    expect(screen.getByText(/We never copy or store your ID/)).toBeInTheDocument()
    expect(screen.getByText(/Already paid. Staff switch your membership on at your next visit/)).toBeInTheDocument()
    expect(await screen.findByAltText('QR code for R7K-42Q')).toBeInTheDocument()
    expect(screen.getAllByText('R7K-42Q')).toHaveLength(1)
    expect(screen.getByRole('link', { name: 'Read the community guidelines now' })).toHaveAttribute('href', '/members/join-feed')
    expect(screen.queryByRole('link', { name: 'Join the community' })).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Verify your age at your next visit.' })).not.toBeInTheDocument()
  })

  it('tells people who had the feed why it closed, and asks for the display name without a door code', async () => {
    membership.me.mockResolvedValue({ membership: null, entitlements: [] })
    feed.path.mockResolvedValue(pathAt('age', { plan: { included: true }, door: { included: true }, age: { notice: true } }))
    renderSettings('/members/home', { user: { ...waiting, has_membership: false, age_check: { verified: false, needed: true, notice: true } } })
    expect(await screen.findByText(/now needs a quick check in person, for everyone/)).toBeInTheDocument()
    expect(screen.getByText(/At the door, give your display name/)).toHaveTextContent('night_owl')
    expect(screen.getAllByText('Included with your account.')).toHaveLength(2)
    expect(screen.queryByAltText(/QR code/)).not.toBeInTheDocument()
  })

  it('shows the verify card in Settings, under Membership', async () => {
    membership.me.mockResolvedValue({ membership: paidWaiting, entitlements: [] })
    renderSettings('/members/settings/membership', { user: waiting })
    expect(await screen.findByRole('region', { name: 'Verify your age at your next visit.' })).toBeInTheDocument()
  })

  it('shows no verify card once the check is on file', async () => {
    membership.me.mockResolvedValue({ membership: active, entitlements: ['feed'] })
    renderSettings('/members/home', { user: { ...verifiedUser, member_app: 'join' } })
    expect(await screen.findByText('Monthly includes')).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Verify your age at your next visit.' })).not.toBeInTheDocument()
  })

  it('explains the check before the guidelines, and lets them accept the guidelines in advance', async () => {
    const account = feedAccountFor({ participating: false, can_join: false, can_view: false, awaiting_age_check: true, accepted_current_guidelines: false })
    feed.get.mockResolvedValue(account)
    feed.acceptGuidelines.mockResolvedValue({ ...account, accepted_current_guidelines: true })
    renderSettings('/members/join-feed', { user: waiting })
    expect(await screen.findByText('First, an age check in person')).toBeInTheDocument()
    expect(screen.getByText('Step 1 of 3 · About')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Read the guidelines' }))
    await userEvent.click(screen.getByLabelText('I agree to the community guidelines'))
    await userEvent.click(screen.getByRole('button', { name: 'Continue' }))
    await waitFor(() => expect(feed.acceptGuidelines).toHaveBeenCalledWith(account.guidelines!.version))
    expect(await screen.findByRole('heading', { name: 'You are ready.' })).toBeInTheDocument()
    expect(screen.getByText('Step 3 of 3 · Age check')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Home' })).toHaveAttribute('href', '/members/home')
  })

  it('goes straight to the profile once checked, when the guidelines were accepted in advance', async () => {
    feed.get.mockResolvedValue(feedAccountFor({ participating: false, can_join: true, can_view: false, awaiting_age_check: false, accepted_current_guidelines: true }))
    renderSettings('/members/join-feed', { user: { ...verifiedUser, member_app: 'join' } })
    await userEvent.click(await screen.findByRole('button', { name: 'Set up your profile' }))
    expect(screen.getByRole('form', { name: 'Set up your feed profile' })).toBeInTheDocument()
  })
})

import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Account } from '@/lib/api'
import type { Metrics, ReportDetail, StaffSession } from '@/lib/safetyApi'
import { renderWithProviders, verifiedUser } from '@/test/render'
import { StaffDashboardPage } from './StaffDashboardPage'
import { StaffReportPage } from './StaffReportPage'

const api = vi.hoisted(() => ({ metrics: vi.fn(), report: vi.fn(), revealReporter: vi.fn(), act: vi.fn(), rules: vi.fn() }))

vi.mock('@/lib/safetyApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/safetyApi')>()
  return { ...actual, staffApi: { ...actual.staffApi, ...api } }
})

const few = { value: null, fewer_than: 5 }

const METRICS: Metrics = {
  range: '30d',
  generated_at: '2026-10-19T12:00:00Z',
  small: 5,
  members: {
    month: 'October 2026',
    total_active: { value: 42 },
    tiers: [{ tier: 'Rose', active: { value: 12 }, new: few, renewing: { value: 6 }, lapsing: few, expired: few }],
  },
  revenue: {
    this_month: { month: 'October 2026', rows: [{ label: 'Rose', cents: 48000 }, { label: 'Donations', cents: null, fewer_than: 5 }], total: { cents: 48000 } },
    last_month: { month: 'September 2026', rows: [{ label: 'Rose', cents: null, fewer_than: 5 }], total: { cents: null, fewer_than: 5 } },
  },
  events: [{ title: 'Member Night', starts_at: '2026-10-10T19:30:00Z', rsvps: { value: 18 }, check_ins: few }],
  feed: { posts: { value: 30 }, comments: { value: 11 }, active_posters_week: few, open_reports: few },
  email_list: { value: 120 },
  series: [
    { label: 'Sep 21', payments: few, revenue: { cents: null, fewer_than: 5 }, rsvps: { value: 6 }, posts: { value: 9 } },
    { label: 'Sep 28', payments: { value: 7 }, revenue: { cents: 28000 }, rsvps: few, posts: { value: 12 } },
  ],
}

function report(overrides: Partial<ReportDetail> = {}): ReportDetail {
  return {
    id: 7,
    kind: 'post',
    kind_label: 'Post',
    reason: 'harassment',
    reason_label: 'Harassment',
    status: 'open',
    status_label: 'Open',
    created_at: '2026-10-19T12:00:00Z',
    assigned_to: null,
    subject: 'velvet_hour',
    subject_is_member: true,
    preview: 'A cruel caption',
    from_website: false,
    details: 'This was aimed at me.',
    content: { caption: 'A cruel caption', status: 'published', is_sensitive: false, images: [] },
    reporter: { hidden: true, can_reveal: false },
    member: { display_name: 'velvet_hour', prior_reports: 2, actions: [] },
    notes: [],
    actions: [],
    team: [{ display_name: 'team_moderator' }],
    ...overrides,
  }
}

function as(staff: Partial<StaffSession> | null): Account {
  const session: StaffSession | null = staff && {
    role: 'moderator',
    door_desk: false,
    verified: true,
    verify_url: null,
    needs_enrollment: false,
    admin_url: '/admin/',
    door_desk_url: null,
    ...staff,
  }
  return { ...verifiedUser, feed_access: true, member_app: 'open', staff: session }
}

beforeEach(() => {
  Object.values(api).forEach((fn) => fn.mockReset())
  api.metrics.mockResolvedValue(METRICS)
  api.report.mockResolvedValue(report())
  api.rules.mockResolvedValue(['Consent first'])
})

function renderReport(user: Account) {
  renderWithProviders(
    <Routes>
      <Route path="/members/staff/reports/:id" element={<StaffReportPage />} />
    </Routes>,
    { user, path: '/members/staff/reports/7' },
  )
}

describe('the staff section', () => {
  it('is a 404 for anyone without a team role', () => {
    renderWithProviders(<StaffDashboardPage />, { user: as(null) })
    expect(screen.getByRole('heading', { name: 'This room is not on the map.' })).toBeInTheDocument()
    expect(api.metrics).not.toHaveBeenCalled()
  })

  it('asks for the two-step login first', () => {
    renderWithProviders(<StaffDashboardPage />, { user: as({ role: 'admin', verified: false, verify_url: 'https://site.example/admin/login/?next=x' }) })
    expect(screen.getByRole('heading', { name: 'Confirm it is you' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Continue' })).toHaveAttribute('href', 'https://site.example/admin/login/?next=x')
    expect(api.metrics).not.toHaveBeenCalled()
  })

  it('starts with setting up an authenticator when there is none', () => {
    renderWithProviders(<StaffDashboardPage />, { user: as({ role: 'admin', verified: false, verify_url: '/admin/login/?next=x', needs_enrollment: true }) })
    expect(screen.getByRole('heading', { name: 'Set up your two-step login' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Set it up' })).toHaveAttribute('href', '/admin/login/?next=x')
  })

  it('shows the metrics to staff, with small numbers withheld', async () => {
    renderWithProviders(<StaffDashboardPage />, { user: as({ role: 'staff', verified: true, verify_url: null }) })
    expect(await screen.findByText('42')).toBeInTheDocument()
    const tiers = screen.getAllByRole('table')[0]
    expect(within(tiers).getAllByText('Fewer than 5').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Fewer than 5 payments').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Reports' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Team' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '12 months' }))
    await waitFor(() => expect(api.metrics).toHaveBeenLastCalledWith('12m'))
  })

  it('keeps reported content hidden until someone chooses to look', async () => {
    renderReport(as({ role: 'moderator', verified: true, verify_url: null }))
    await userEvent.click(await screen.findByRole('button', { name: 'View reported content' }))
    expect(screen.getByText('A cruel caption')).toBeVisible()
    expect(screen.getByText('This was aimed at me.')).toBeInTheDocument()
    expect(screen.getByText(/Hidden. The reported member is never told/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Reveal/ })).not.toBeInTheDocument()
    expect(screen.getByText(/2 earlier reports/)).toBeInTheDocument()
  })

  it('lets only an admin reveal the reporter, and says it is logged', async () => {
    api.report.mockResolvedValue(report({ reporter: { hidden: true, can_reveal: true } }))
    api.revealReporter.mockResolvedValue({ display_name: 'quiet_reporter', contact_email: '' })
    renderReport(as({ role: 'admin', verified: true, verify_url: null }))
    await userEvent.click(await screen.findByRole('button', { name: 'Reveal (logged)' }))
    expect(await screen.findByText(/quiet_reporter/)).toBeInTheDocument()
    expect(screen.getByText(/it is in the log/)).toBeInTheDocument()
  })

  it('needs a rule and a reason before recording an action', async () => {
    api.act.mockResolvedValue({ id: 1, kind: 'feed_suspension', kind_label: 'Feed suspension' })
    renderReport(as({ role: 'moderator', verified: true, verify_url: null }))
    await userEvent.click(await screen.findByRole('button', { name: 'Take action' }))
    const dialog = screen.getByRole('dialog', { name: 'Action on velvet_hour' })
    await userEvent.click(within(dialog).getByRole('radio', { name: /Feed suspension/ }))
    await userEvent.click(within(dialog).getByRole('button', { name: 'Record action' }))
    expect(within(dialog).getByRole('alert')).toHaveTextContent('Choose the rule this relates to.')
    await userEvent.type(within(dialog).getByLabelText(/^Rule/), 'Consent first')
    await userEvent.type(within(dialog).getByLabelText(/^Reason/), 'Posted a photo without asking.')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Record action' }))
    await waitFor(() =>
      expect(api.act).toHaveBeenCalledWith('velvet_hour', expect.objectContaining({ kind: 'feed_suspension', rule: 'Consent first', days: 7, report_id: 7 })),
    )
  })
})

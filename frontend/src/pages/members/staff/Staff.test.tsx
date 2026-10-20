import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Account } from '@/lib/api'
import type { ReportDetail, StaffSession } from '@/lib/safetyApi'
import { renderWithProviders, verifiedUser } from '@/test/render'
import { StaffIndexPage } from './StaffIndexPage'
import { StaffReportPage } from './StaffReportPage'
import { StaffReportsPage } from './StaffReportsPage'

const api = vi.hoisted(() => ({ reports: vi.fn(), appeals: vi.fn(), report: vi.fn(), revealReporter: vi.fn(), act: vi.fn(), rules: vi.fn() }))

vi.mock('@/lib/safetyApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/safetyApi')>()
  return { ...actual, staffApi: { ...actual.staffApi, ...api } }
})

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
    admin_url: '/admin/', age_check_required: true, can_change_age_check: false, age_check_url: 'https://site.example/admin/pages/sitesettings/age-verification/',
    ...staff,
  }
  return { ...verifiedUser, feed_access: true, member_app: 'open', staff: session }
}

beforeEach(() => {
  Object.values(api).forEach((fn) => fn.mockReset())
  api.reports.mockResolvedValue([])
  api.appeals.mockResolvedValue([])
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
    renderWithProviders(<StaffReportsPage />, { user: as(null) })
    expect(screen.getByRole('heading', { name: 'This room is not on the map.' })).toBeInTheDocument()
    expect(api.reports).not.toHaveBeenCalled()
  })

  it('asks for the two-step login first', () => {
    renderWithProviders(<StaffReportsPage />, { user: as({ role: 'admin', verified: false, verify_url: 'https://site.example/admin/login/?next=x' }) })
    expect(screen.getByRole('heading', { name: 'Confirm it is you' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Continue' })).toHaveAttribute('href', 'https://site.example/admin/login/?next=x')
    expect(api.reports).not.toHaveBeenCalled()
  })

  it('starts with setting up an authenticator when there is none', () => {
    renderWithProviders(<StaffReportsPage />, { user: as({ role: 'admin', verified: false, verify_url: '/admin/login/?next=x', needs_enrollment: true }) })
    expect(screen.getByRole('heading', { name: 'Set up your two-step login' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Set it up' })).toHaveAttribute('href', '/admin/login/?next=x')
  })

  it('has no dashboard or figures: its tabs are the tools, and Dashboard opens the admin', async () => {
    renderWithProviders(<StaffReportsPage />, { user: as({ role: 'admin', door_desk: true }) })
    const nav = screen.getByRole('navigation', { name: 'Staff' })
    const links = within(nav).getAllByRole('link').map((link) => [link.textContent, link.getAttribute('href')])
    expect(links).toEqual([
      ['Door desk', '/members/staff/door'],
      ['Reports', '/members/staff/reports'],
      ['Members', '/members/staff/members'],
      ['Team', '/members/staff/team'],
      ['Dashboard(opens the admin)', '/admin/'],
    ])
    await waitFor(() => expect(api.reports).toHaveBeenCalled())
  })

  it('shows a moderator the tools and the dashboard link, but not Team', () => {
    renderWithProviders(<StaffReportsPage />, { user: as({ role: 'moderator' }) })
    const names = within(screen.getByRole('navigation', { name: 'Staff' }))
      .getAllByRole('link')
      .map((link) => link.textContent)
    expect(names).toEqual(['Reports', 'Members', 'Dashboard(opens the admin)'])
  })

  it('sends /members/staff to the reports inbox, and a door volunteer to the door desk', () => {
    renderWithProviders(
      <Routes>
        <Route path="/members/staff" element={<StaffIndexPage />} />
        <Route path="/members/staff/reports" element={<p>Inbox</p>} />
      </Routes>,
      { user: as({ role: 'moderator' }), path: '/members/staff' },
    )
    expect(screen.getByText('Inbox')).toBeInTheDocument()
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

describe('the age verification banner', () => {
  it('shows on staff pages while it is off, linking admins to the setting', () => {
    renderWithProviders(<StaffReportsPage />, { user: as({ role: 'admin', age_check_required: false, can_change_age_check: true }) })
    expect(screen.getByRole('link', { name: /Age verification for the member feed is off/ })).toHaveAttribute(
      'href',
      'https://site.example/admin/pages/sitesettings/age-verification/',
    )
  })

  it('shows without a way to change it to everyone else, and not at all while it is on', () => {
    const { unmount } = renderWithProviders(<StaffReportsPage />, { user: as({ role: 'moderator', age_check_required: false }) })
    expect(screen.getByText('Age verification for the member feed is off')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Age verification/ })).not.toBeInTheDocument()
    unmount()
    renderWithProviders(<StaffReportsPage />, { user: as({ role: 'moderator' }) })
    expect(screen.queryByText('Age verification for the member feed is off')).not.toBeInTheDocument()
  })
})

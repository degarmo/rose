import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { MemberActionData } from '@/lib/safetyApi'
import { renderWithProviders, verifiedUser } from '@/test/render'
import { NoticesPage } from './NoticesPage'

const api = vi.hoisted(() => ({ notices: vi.fn(), myReports: vi.fn(), appeal: vi.fn() }))

vi.mock('@/lib/safetyApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/safetyApi')>()
  return { ...actual, safetyApi: { ...actual.safetyApi, ...api } }
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

beforeEach(() => {
  Object.values(api).forEach((fn) => fn.mockReset())
  api.notices.mockResolvedValue([suspension])
  api.myReports.mockResolvedValue([{ id: 9, kind_label: 'Post', created_at: '2026-10-18T12:00:00Z', status: 'reviewed' }])
})

describe('NoticesPage', () => {
  it('shows the decision, its rule and reason, and the reports sent as received or reviewed', async () => {
    renderWithProviders(<NoticesPage />, { user: verifiedUser })
    expect(await screen.findByRole('heading', { name: 'Feed suspension' })).toBeInTheDocument()
    expect(screen.getByText(/Consent first/)).toBeInTheDocument()
    expect(screen.getByText('A photo was posted without asking.')).toBeInTheDocument()
    expect(await screen.findByText('Reviewed')).toBeInTheDocument()
  })

  it('sends one appeal and then shows it waiting', async () => {
    api.appeal.mockResolvedValue({
      ...suspension,
      appeal: { id: 1, status: 'open', status_label: 'Open', created_at: '2026-10-19T13:00:00Z', decided_at: null },
    })
    renderWithProviders(<NoticesPage />, { user: verifiedUser })
    await userEvent.click(await screen.findByRole('button', { name: 'Appeal this decision' }))
    await userEvent.type(screen.getByLabelText(/Your appeal/), 'I had asked them first.')
    await userEvent.click(screen.getByRole('button', { name: 'Send appeal' }))
    await waitFor(() => expect(api.appeal).toHaveBeenCalledWith(3, 'I had asked them first.'))
    expect(await screen.findByText(/waiting for review/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Appeal this decision' })).not.toBeInTheDocument()
  })
})

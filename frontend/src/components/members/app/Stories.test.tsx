import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { StoryGroup } from '@/lib/membersApi'
import { renderInApp } from '@/test/members'
import { StoriesTray } from './Stories'

const api = vi.hoisted(() => ({ stories: vi.fn(), markStoriesSeen: vi.fn() }))

vi.mock('@/lib/membersApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membersApi')>()
  return { ...actual, members: { ...actual.members, ...api } }
})

function item(key: string, seen: boolean, title = key) {
  return { key, kind: 'event' as const, title, text: 'A summary.', starts_at: new Date().toISOString(), image: null, link: { label: 'RSVP', url: `/events/${key}` }, seen }
}

const groups: StoryGroup[] = [
  { id: 'this-week', title: 'This week', seen: false, items: [item('event:a', true, 'Friday Social'), item('event:b', false, 'Saturday Social')] },
  { id: 'news', title: 'News', seen: true, items: [{ ...item('announcement:1', true, 'Coat check'), kind: 'announcement' }] },
]

beforeEach(() => {
  api.stories.mockReset().mockResolvedValue({ results: groups })
  api.markStoriesSeen.mockReset().mockResolvedValue({ ok: true })
})

describe('StoriesTray', () => {
  it('rings unseen circles in rose and seen ones in grey', async () => {
    renderInApp(<StoriesTray />)
    const unseen = await screen.findByRole('button', { name: 'This week, new' })
    const seen = screen.getByRole('button', { name: 'News, seen' })
    expect(unseen.querySelector('.border-primary')).not.toBeNull()
    expect(seen.querySelector('.border-border')).not.toBeNull()
    expect(seen.querySelector('.border-primary')).toBeNull()
  })

  it('opens full screen, marks what is shown as seen, and moves with the arrow keys', async () => {
    renderInApp(<StoriesTray />)
    await userEvent.click(await screen.findByRole('button', { name: 'This week, new' }))
    const viewer = screen.getByRole('dialog', { name: 'This week stories' })
    expect(within(viewer).getByRole('heading', { name: 'Friday Social' })).toBeInTheDocument()
    // Already seen: nothing to record.
    expect(api.markStoriesSeen).not.toHaveBeenCalled()

    fireEvent.keyDown(viewer, { key: 'ArrowRight' })
    expect(within(viewer).getByRole('heading', { name: 'Saturday Social' })).toBeInTheDocument()
    await waitFor(() => expect(api.markStoriesSeen).toHaveBeenCalledWith(['event:b']))
    expect(within(viewer).getByRole('link', { name: 'RSVP' })).toHaveAttribute('href', '/events/event:b')
  })
})

import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { JournalPost } from '@/lib/api'
import { renderWithProviders } from '@/test/render'
import { JournalStrip, JOURNAL_STRIP_COUNT } from './JournalStrip'

const journal = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return { ...actual, api: { ...actual.api, journal } }
})

function post(n: number): JournalPost {
  return {
    slug: `post-${n}`,
    caption_html: `Club note ${n}`,
    published_at: new Date(Date.now() - n * 3600_000).toISOString(),
    author: null,
    images: [{ url: `/media/journal/${n}.webp`, alt: `Picture ${n}`, width: 1080, height: 1080, srcset: null }],
    event: null,
    cta: null,
  }
}

beforeEach(() => journal.mockReset())

describe('JournalStrip', () => {
  it('shows the latest posts as tiles, newest first, at most six', async () => {
    journal.mockResolvedValue({ posts: Array.from({ length: 8 }, (_, n) => post(n + 1)), nextCursor: null })
    renderWithProviders(<JournalStrip />)
    const list = await screen.findByRole('list', { name: 'Latest journal posts' })
    const tiles = screen.getAllByRole('button', { name: /^Open post:/ })
    expect(tiles).toHaveLength(JOURNAL_STRIP_COUNT)
    expect(tiles[0]).toHaveAccessibleName('Open post: Club note 1')
    expect(list.querySelector('img')).toHaveAttribute('src', '/media/journal/1.webp')
  })

  it('keeps a visible placeholder under each picture while it loads', async () => {
    journal.mockResolvedValue({ posts: [post(1)], nextCursor: null })
    renderWithProviders(<JournalStrip />)
    const tile = await screen.findByRole('button', { name: 'Open post: Club note 1' })
    expect(tile.querySelector('[class*="texture-"]')).not.toBeNull()
    expect(tile.querySelector('img')).not.toBeNull()
  })

  it('says so plainly when there are no posts yet', async () => {
    journal.mockResolvedValue({ posts: [], nextCursor: null })
    renderWithProviders(<JournalStrip />)
    expect(await screen.findByText('The first posts are on their way')).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Latest journal posts' })).not.toBeInTheDocument()
  })
})

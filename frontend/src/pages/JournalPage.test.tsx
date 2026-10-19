import { act, fireEvent, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { JournalPost } from '@/lib/api'
import { renderWithProviders } from '@/test/render'
import { JournalPage } from './JournalPage'

const apiMock = vi.hoisted(() => ({ journal: vi.fn() }))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return { ...actual, api: { ...actual.api, ...apiMock } }
})

function post(slug: string, images: number, extra: Partial<JournalPost> = {}): JournalPost {
  return {
    slug,
    caption_html: `Caption for ${slug}<br>second line`,
    published_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    author: 'editor_one',
    images: Array.from({ length: images }, (_, i) => ({ url: `/media/${slug}-${i}.webp`, alt: `Image ${i + 1} alt` })),
    event: null,
    cta: null,
    ...extra,
  }
}

beforeEach(() => {
  apiMock.journal.mockReset()
})

async function openFirstPost() {
  renderWithProviders(<JournalPage />)
  await userEvent.click(await screen.findByRole('button', { name: /Open post: Caption for gallery/ }))
  return screen.getByRole('dialog', { hidden: true })
}

describe('Journal modal carousel', () => {
  beforeEach(() => {
    apiMock.journal.mockResolvedValue({
      posts: [
        post('gallery', 3, { event: { slug: 'friday-social', title: 'Friday Social', starts_at: '2026-11-06T21:00:00-06:00' } }),
        post('single', 1, { cta: { label: 'Request a mentor', url: '/contact' } }),
      ],
      nextCursor: null,
    })
  })

  it('opens the post in a modal with caption, relative date and RSVP link', async () => {
    const dialog = await openFirstPost()
    expect(dialog).toHaveAttribute('open')
    expect(within(dialog).getByText(/Caption for gallery/)).toBeInTheDocument()
    expect(within(dialog).getByText('2 days ago')).toBeInTheDocument()
    expect(within(dialog).getByRole('link', { name: 'RSVP' })).toHaveAttribute('href', '/events/friday-social')
    expect(within(dialog).getByRole('link', { name: /Open as a page/ })).toHaveAttribute('href', '/journal/gallery')
  })

  it('moves between images with buttons and the keyboard', async () => {
    const dialog = await openFirstPost()
    const carousel = within(dialog).getByRole('region', { name: 'Post images' })
    expect(within(carousel).getByText('Image 1 of 3')).toBeInTheDocument()
    expect(within(carousel).getByRole('button', { name: 'Previous image' })).toBeDisabled()

    await userEvent.click(within(carousel).getByRole('button', { name: 'Next image' }))
    expect(within(carousel).getByText('Image 2 of 3')).toBeInTheDocument()

    carousel.focus()
    await userEvent.keyboard('{ArrowRight}')
    expect(within(carousel).getByText('Image 3 of 3')).toBeInTheDocument()
    expect(within(carousel).getByRole('button', { name: 'Next image' })).toBeDisabled()

    await userEvent.keyboard('{ArrowRight}')
    expect(within(carousel).getByText('Image 3 of 3')).toBeInTheDocument()
    await userEvent.keyboard('{ArrowLeft}')
    expect(within(carousel).getByText('Image 2 of 3')).toBeInTheDocument()
  })

  it('swipes on touch', async () => {
    const dialog = await openFirstPost()
    const carousel = within(dialog).getByRole('region', { name: 'Post images' })
    act(() => {
      fireEvent.touchStart(carousel, { touches: [{ clientX: 300 }] })
      fireEvent.touchEnd(carousel, { changedTouches: [{ clientX: 120 }] })
    })
    expect(within(carousel).getByText('Image 2 of 3')).toBeInTheDocument()
    act(() => {
      fireEvent.touchStart(carousel, { touches: [{ clientX: 100 }] })
      fireEvent.touchEnd(carousel, { changedTouches: [{ clientX: 120 }] })
    })
    expect(within(carousel).getByText('Image 2 of 3')).toBeInTheDocument()
    act(() => {
      fireEvent.touchStart(carousel, { touches: [{ clientX: 100 }] })
      fireEvent.touchEnd(carousel, { changedTouches: [{ clientX: 300 }] })
    })
    expect(within(carousel).getByText('Image 1 of 3')).toBeInTheDocument()
  })

  it('marks multi-image tiles and uses the CTA when there is no event', async () => {
    renderWithProviders(<JournalPage />)
    const single = await screen.findByRole('button', { name: /Open post: Caption for single/ })
    const gallery = screen.getByRole('button', { name: /Open post: Caption for gallery/ })
    expect(gallery.querySelector('svg.lucide-layers')).not.toBeNull()
    expect(single.querySelector('svg.lucide-layers')).toBeNull()

    await userEvent.click(single)
    const dialog = screen.getByRole('dialog', { hidden: true })
    expect(within(dialog).getByRole('link', { name: 'Request a mentor' })).toHaveAttribute('href', '/contact')
    expect(within(dialog).queryByRole('button', { name: 'Next image' })).not.toBeInTheDocument()
  })

  it('closes the modal', async () => {
    const dialog = await openFirstPost()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Close' }))
    expect(dialog).not.toHaveAttribute('open')
  })
})

describe('Journal pagination', () => {
  it('loads more with the cursor from the previous page', async () => {
    apiMock.journal
      .mockResolvedValueOnce({ posts: [post('one', 1)], nextCursor: 'abc' })
      .mockResolvedValueOnce({ posts: [post('two', 1)], nextCursor: null })
    renderWithProviders(<JournalPage />)
    await userEvent.click(await screen.findByRole('button', { name: 'Load more' }))
    expect(apiMock.journal).toHaveBeenLastCalledWith('abc')
    expect(await screen.findByRole('button', { name: /Caption for two/ })).toBeInTheDocument()
    expect(screen.getByText('You are all caught up.')).toBeInTheDocument()
  })

  it('shows an error state with retry', async () => {
    apiMock.journal.mockRejectedValueOnce(new Error('down')).mockResolvedValueOnce({ posts: [], nextCursor: null })
    renderWithProviders(<JournalPage />)
    await userEvent.click(await screen.findByRole('button', { name: /Try again/ }))
    expect(await screen.findByText('Nothing here yet')).toBeInTheDocument()
  })
})

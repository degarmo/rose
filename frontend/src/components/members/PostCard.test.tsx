import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { FeedPost } from '@/lib/membersApi'
import { renderWithProviders } from '@/test/render'
import { PostCard } from './PostCard'

const api = vi.hoisted(() => ({
  like: vi.fn(),
  unlike: vi.fn(),
  report: vi.fn(),
  relate: vi.fn(),
  deletePost: vi.fn(),
  editPost: vi.fn(),
}))

vi.mock('@/lib/membersApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membersApi')>()
  return { ...actual, members: { ...actual.members, ...api } }
})

function makePost(overrides: Partial<FeedPost> = {}): FeedPost {
  return {
    id: 'p1',
    author: { handle: 'velvet_hour', avatar: null },
    caption_html: 'Candles and quiet',
    caption: null,
    posted: { recent: true, at: new Date(Date.now() - 3600_000).toISOString(), month: null },
    edited: false,
    images: [
      { id: 'i1', url: '/api/members/media/i1/', alt: 'First' },
      { id: 'i2', url: '/api/members/media/i2/', alt: 'Second' },
    ],
    is_sensitive: false,
    blur: false,
    comments_enabled: true,
    comment_count: 2,
    liked_by_me: false,
    like_count: null,
    is_own: false,
    state: null,
    in_review: null,
    ...overrides,
  }
}

function renderCard(post: FeedPost) {
  const onChange = vi.fn()
  renderWithProviders(<PostCard post={post} onChange={onChange} />)
  return { onChange }
}

beforeEach(() => Object.values(api).forEach((fn) => fn.mockReset()))

async function openMenu() {
  await userEvent.click(screen.getByRole('button', { name: 'Post options' }))
}

describe('PostCard', () => {
  it('blurs sensitive images until the viewer chooses to look', async () => {
    renderCard(makePost({ is_sensitive: true, blur: true }))
    const carousel = screen.getByRole('region', { name: /Images in velvet_hour/, hidden: true })
    expect(carousel.closest('[aria-hidden="true"]')).not.toBeNull()
    expect(screen.getByText('Marked sensitive by the author')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'View' }))
    expect(screen.queryByText('Marked sensitive by the author')).not.toBeInTheDocument()
    expect(screen.getByRole('region', { name: /Images in velvet_hour/ }).closest('[aria-hidden="true"]')).toBeNull()
  })

  it('does not blur when the API says not to', () => {
    renderCard(makePost({ is_sensitive: true, blur: false }))
    expect(screen.queryByRole('button', { name: 'View' })).not.toBeInTheDocument()
  })

  it('protects images from save and drag', () => {
    renderCard(makePost())
    const image = screen.getAllByRole('img', { hidden: true }).find((el) => el.getAttribute('src') === '/api/members/media/i1/')
    expect(image).toHaveAttribute('draggable', 'false')
    expect(image?.className).toContain('select-none')
  })

  it('likes optimistically and shows no count to other viewers', async () => {
    let resolve: (post: FeedPost) => void = () => undefined
    api.like.mockReturnValue(new Promise((r) => (resolve = r)))
    const { onChange } = renderCard(makePost())
    await userEvent.click(screen.getByRole('button', { name: 'Like' }))
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ liked_by_me: true, like_count: null }))
    resolve(makePost({ liked_by_me: true }))
    await waitFor(() => expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ liked_by_me: true })))
    expect(screen.queryByText(/likes?$/)).not.toBeInTheDocument()
  })

  it('shows the like count to the author only', () => {
    renderCard(makePost({ is_own: true, like_count: 3, state: 'published' }))
    expect(screen.getByText('3 likes')).toBeInTheDocument()
  })

  it('reports through the overflow menu without revealing anything back', async () => {
    api.report.mockResolvedValue({ detail: 'Thanks, our team will review this.' })
    renderCard(makePost())
    await openMenu()
    await userEvent.click(screen.getByRole('button', { name: 'Report' }))
    const dialog = screen.getByRole('dialog', { name: 'Report this post', hidden: true })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Send report' }))
    expect(within(dialog).getByRole('alert')).toHaveTextContent('Choose a reason.')
    await userEvent.click(within(dialog).getByLabelText('Posted without consent'))
    await userEvent.click(within(dialog).getByRole('button', { name: 'Send report' }))
    expect(api.report).toHaveBeenCalledWith('post', 'p1', 'no_consent', '')
    expect(await screen.findByText('Thanks, our team will review this.')).toBeInTheDocument()
  })

  it('mutes from the menu and removes the post from the list', async () => {
    api.relate.mockResolvedValue({ ok: true })
    const { onChange } = renderCard(makePost())
    await openMenu()
    await userEvent.click(screen.getByRole('button', { name: 'Mute velvet_hour' }))
    expect(api.relate).toHaveBeenCalledWith('velvet_hour', 'mute')
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(null))
  })

  it('confirms before blocking', async () => {
    api.relate.mockResolvedValue({ ok: true })
    const { onChange } = renderCard(makePost())
    await openMenu()
    await userEvent.click(screen.getByRole('button', { name: 'Block velvet_hour' }))
    expect(api.relate).not.toHaveBeenCalled()
    const dialog = screen.getByRole('dialog', { name: 'Block velvet_hour?', hidden: true })
    expect(within(dialog).getByText(/They are not told/)).toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Block' }))
    expect(api.relate).toHaveBeenCalledWith('velvet_hour', 'block')
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(null))
  })

  it('offers edit and delete on your own post, with confirmation', async () => {
    api.deletePost.mockResolvedValue(null)
    const { onChange } = renderCard(makePost({ is_own: true, like_count: 0, state: 'published' }))
    await openMenu()
    expect(screen.queryByRole('button', { name: 'Report' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
    expect(api.deletePost).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Delete for good' }))
    expect(api.deletePost).toHaveBeenCalledWith('p1')
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(null))
  })

  it('shows the review state to the author', () => {
    renderCard(makePost({ is_own: true, like_count: 0, state: 'pending' }))
    expect(screen.getByText('Waiting for review')).toBeInTheDocument()
  })
})

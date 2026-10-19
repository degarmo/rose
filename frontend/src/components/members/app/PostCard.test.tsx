import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ClubPost, FeedPost } from '@/lib/membersApi'
import { makePost, renderInApp } from '@/test/members'
import { PostCard } from './PostCard'

const api = vi.hoisted(() => ({
  like: vi.fn(),
  unlike: vi.fn(),
  save: vi.fn(),
  unsave: vi.fn(),
  report: vi.fn(),
  relate: vi.fn(),
  hide: vi.fn(),
  deletePost: vi.fn(),
  editPost: vi.fn(),
  addComment: vi.fn(),
}))

vi.mock('@/lib/membersApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membersApi')>()
  return { ...actual, members: { ...actual.members, ...api } }
})

beforeEach(() => Object.values(api).forEach((fn) => fn.mockReset()))

function renderCard(post: FeedPost | ClubPost, listIds?: string[]) {
  return renderInApp(<PostCard post={post} listIds={listIds} />)
}

async function openSheet() {
  await userEvent.click(screen.getByRole('button', { name: 'Post options' }))
  return screen.getByRole('dialog', { name: 'Post options', hidden: true })
}

describe('PostCard', () => {
  it('lays out header, media, actions, likes, caption, comments, time and the comment box in order', () => {
    const comment = { id: 'c1', author: { handle: 'moth', avatar: null }, body_html: 'Lovely', posted: { recent: true, at: new Date().toISOString(), month: null }, can_delete: false }
    renderCard(makePost({ is_own: true, like_count: 4, state: 'published', comment_count: 3, recent_comments: [comment] }))
    const article = screen.getByRole('article', { name: 'Post by velvet_hour' })
    const order = [
      within(article).getByRole('button', { name: 'Post options' }),
      within(article).getByRole('region', { name: /Images in velvet_hour/ }),
      within(article).getByRole('button', { name: 'Like' }),
      within(article).getByText('4 likes'),
      within(article).getByText('Candles and quiet'),
      within(article).getByRole('button', { name: 'View all 3 comments' }),
      within(article).getByText('Lovely'),
      within(article).getAllByText(/ago$/).at(-1) as HTMLElement,
      within(article).getByRole('textbox', { name: 'Add a comment' }),
    ]
    for (let i = 1; i < order.length; i += 1) {
      expect(order[i - 1].compareDocumentPosition(order[i]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    }
  })

  it('takes its shape from the first image, clamped between 4:5 and 1.91:1', () => {
    const { unmount } = renderCard(makePost({ images: [{ id: 'i1', url: '/a', alt: '', width: 400, height: 1200 }] }))
    expect(screen.getByRole('region', { name: /Images/ }).style.aspectRatio).toMatch(/^0\.8( \/ 1)?$/)
    unmount()
    renderCard(makePost({ images: [{ id: 'i1', url: '/a', alt: '', width: 3000, height: 1000 }] }))
    expect(screen.getByRole('region', { name: /Images/ }).style.aspectRatio).toMatch(/^1\.91( \/ 1)?$/)
  })

  it('blurs sensitive images until the viewer chooses to look', async () => {
    renderCard(makePost({ is_sensitive: true, blur: true }))
    const carousel = screen.getByRole('region', { name: /Images in velvet_hour/, hidden: true })
    // Inert while blurred: nothing inside can be focused or read out.
    expect(carousel.closest('[inert]')).not.toBeNull()
    await userEvent.click(screen.getByRole('button', { name: 'View' }))
    expect(screen.getByRole('region', { name: /Images in velvet_hour/ }).closest('[inert]')).toBeNull()
  })

  it('protects images from save and drag', () => {
    renderCard(makePost())
    const image = screen.getAllByRole('img', { hidden: true }).find((el) => el.getAttribute('src') === '/api/members/media/i1/')
    expect(image).toHaveAttribute('draggable', 'false')
    expect(image?.className).toContain('select-none')
  })

  describe('likes line', () => {
    it('shows other viewers nothing until they like it, then only "Liked by you"', async () => {
      api.like.mockResolvedValue(makePost({ liked_by_me: true }))
      renderCard(makePost())
      expect(screen.queryByText(/likes?$/)).not.toBeInTheDocument()
      expect(screen.queryByText('Liked by you')).not.toBeInTheDocument()
      await userEvent.click(screen.getByRole('button', { name: 'Like' }))
      expect(await screen.findByText('Liked by you')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Liked' })).toHaveAttribute('aria-pressed', 'true')
      expect(screen.queryByText(/\d+ likes?/)).not.toBeInTheDocument()
    })

    it('shows the author the count, as plain text with no list behind it', () => {
      renderCard(makePost({ is_own: true, like_count: 1, state: 'published' }))
      const line = screen.getByText('1 like')
      expect(line.tagName).toBe('P')
      expect(line.closest('a, button')).toBeNull()
    })
  })

  describe('double-tap to like', () => {
    it('likes on a double-click and shows the heart burst', async () => {
      api.like.mockResolvedValue(makePost({ liked_by_me: true }))
      renderCard(makePost())
      fireEvent.doubleClick(screen.getByRole('region', { name: /Images/ }))
      expect(api.like).toHaveBeenCalledWith('p1')
      expect(document.querySelector('.animate-heart-burst')).not.toBeNull()
      expect(await screen.findByText('Liked by you')).toBeInTheDocument()
    })

    it('likes on two quick taps', () => {
      api.like.mockResolvedValue(makePost({ liked_by_me: true }))
      renderCard(makePost())
      const media = screen.getByRole('region', { name: /Images/ })
      for (const timeStamp of [1000, 1200]) {
        fireEvent.pointerDown(media, { pointerType: 'touch', clientX: 100 })
        fireEvent.pointerUp(media, { pointerType: 'touch', clientX: 100, timeStamp })
      }
      expect(api.like).toHaveBeenCalledTimes(1)
    })

    it('never takes a like away', () => {
      renderCard(makePost({ liked_by_me: true }))
      fireEvent.doubleClick(screen.getByRole('region', { name: /Images/ }))
      expect(api.unlike).not.toHaveBeenCalled()
      expect(api.like).not.toHaveBeenCalled()
    })
  })

  it('saves privately with the bookmark', async () => {
    api.save.mockResolvedValue(makePost({ saved_by_me: true }))
    renderCard(makePost())
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(api.save).toHaveBeenCalledWith('p1')
    expect(screen.getByRole('button', { name: 'Saved' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('reports through the centred action sheet', async () => {
    api.report.mockResolvedValue({ detail: 'Thanks, our team will review this.' })
    renderCard(makePost())
    const sheet = await openSheet()
    await userEvent.click(within(sheet).getByRole('button', { name: 'Report to hosts', hidden: true }))
    const dialog = screen.getByRole('dialog', { name: 'Report this post', hidden: true })
    await userEvent.click(within(dialog).getByLabelText('Posted without consent'))
    await userEvent.click(within(dialog).getByRole('button', { name: 'Send report' }))
    expect(api.report).toHaveBeenCalledWith('post', 'p1', 'no_consent', '')
    expect(await screen.findByText('Thanks, our team will review this.')).toBeInTheDocument()
  })

  it('mutes from the sheet and drops the post', async () => {
    api.relate.mockResolvedValue({ ok: true })
    renderCard(makePost())
    const sheet = await openSheet()
    await userEvent.click(within(sheet).getByRole('button', { name: 'Mute velvet_hour', hidden: true }))
    expect(api.relate).toHaveBeenCalledWith('velvet_hour', 'mute')
    await waitFor(() => expect(screen.queryByRole('article')).not.toBeInTheDocument())
  })

  it('hides a post from your own feed and drops it', async () => {
    api.hide.mockResolvedValue({ ok: true })
    renderCard(makePost())
    const sheet = await openSheet()
    // Report comes first, and there is no Share, Send or Copy link.
    const labels = within(sheet)
      .getAllByRole('button', { hidden: true })
      .map((button) => button.textContent)
    expect(labels).toEqual(['Report to hosts', 'Hide this post', 'Mute velvet_hour', 'Block velvet_hour', 'Save', 'Go to post', 'Cancel'])
    await userEvent.click(within(sheet).getByRole('button', { name: 'Hide this post', hidden: true }))
    expect(api.hide).toHaveBeenCalledWith('p1')
    await waitFor(() => expect(screen.queryByRole('article')).not.toBeInTheDocument())
  })

  it('confirms before blocking', async () => {
    api.relate.mockResolvedValue({ ok: true })
    renderCard(makePost())
    const sheet = await openSheet()
    await userEvent.click(within(sheet).getByRole('button', { name: 'Block velvet_hour', hidden: true }))
    expect(api.relate).not.toHaveBeenCalled()
    const dialog = screen.getByRole('dialog', { name: 'Block velvet_hour?', hidden: true })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Block', hidden: true }))
    expect(api.relate).toHaveBeenCalledWith('velvet_hour', 'block')
  })

  it('offers edit and delete on your own post, with confirmation', async () => {
    api.deletePost.mockResolvedValue(null)
    renderCard(makePost({ is_own: true, like_count: 0, state: 'published' }))
    const sheet = await openSheet()
    expect(within(sheet).queryByRole('button', { name: 'Report to hosts', hidden: true })).not.toBeInTheDocument()
    await userEvent.click(within(sheet).getByRole('button', { name: 'Delete', hidden: true }))
    expect(api.deletePost).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Delete for good', hidden: true }))
    expect(api.deletePost).toHaveBeenCalledWith('p1')
  })

  it('posts a comment inline; Post lights up only with text', async () => {
    const comment = { id: 'c9', author: { handle: 'night_owl', avatar: null }, body_html: 'Same here', posted: { recent: true, at: new Date().toISOString(), month: null }, can_delete: true }
    api.addComment.mockResolvedValue(comment)
    renderCard(makePost())
    const post = screen.getByRole('button', { name: 'Post' })
    expect(post).toBeDisabled()
    await userEvent.type(screen.getByRole('textbox', { name: 'Add a comment' }), 'Same here')
    expect(post).toBeEnabled()
    expect(post.className).toContain('text-link')
    await userEvent.click(post)
    expect(api.addComment).toHaveBeenCalledWith('p1', 'Same here')
    expect(await screen.findByText('Same here')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'View 1 comment' })).toBeInTheDocument()
  })

  it('keeps a comment made while a like is still on its way', async () => {
    let finishLike: (post: FeedPost) => void = () => undefined
    api.like.mockReturnValue(new Promise((resolve) => (finishLike = resolve)))
    const comment = { id: 'c5', author: { handle: 'night_owl', avatar: null }, body_html: 'Quick note', posted: { recent: true, at: new Date().toISOString(), month: null }, can_delete: true }
    api.addComment.mockResolvedValue(comment)
    renderCard(makePost())
    await userEvent.click(screen.getByRole('button', { name: 'Like' }))
    await userEvent.type(screen.getByRole('textbox', { name: 'Add a comment' }), 'Quick note')
    await userEvent.click(screen.getByRole('button', { name: 'Post' }))
    expect(await screen.findByText('Quick note')).toBeInTheDocument()
    // The like's reply is the server's copy from before the comment.
    finishLike(makePost({ liked_by_me: true }))
    await waitFor(() => expect(screen.getByText('Liked by you')).toBeInTheDocument())
    expect(screen.getByText('Quick note')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'View 1 comment' })).toBeInTheDocument()
  })

  it('opens the post with the list around it', async () => {
    const { openPost } = renderCard(makePost({ comment_count: 5 }), ['p0', 'p1', 'p2'])
    await userEvent.click(screen.getByRole('button', { name: 'View all 5 comments' }))
    expect(openPost).toHaveBeenCalledWith('p1', ['p0', 'p1', 'p2'])
  })

  it('shows the review state to the author', () => {
    renderCard(makePost({ is_own: true, like_count: 0, state: 'pending' }))
    expect(screen.getByText('Waiting for review')).toBeInTheDocument()
  })

  it('shows a journal post as the club "Rose" account, linking to the website', () => {
    const club: ClubPost = {
      kind: 'club',
      id: 'club-spring',
      slug: 'spring',
      author: { handle: 'Rose', avatar: null },
      caption_html: 'Spring classes are open',
      posted: { recent: true, at: new Date().toISOString(), month: null },
      images: [{ id: 'spring-0', url: '/media/journal/a.webp', alt: 'Candles', width: 1200, height: 900 }],
      link: { label: 'Learn more', url: '/journal/spring' },
    }
    renderCard(club)
    const article = screen.getByRole('article', { name: 'Post by Rose' })
    expect(within(article).getByRole('link', { name: 'Learn more' })).toHaveAttribute('href', '/journal/spring')
    expect(within(article).queryByRole('button', { name: 'Like' })).not.toBeInTheDocument()
    expect(within(article).queryByRole('button', { name: 'Post options' })).not.toBeInTheDocument()
  })
})

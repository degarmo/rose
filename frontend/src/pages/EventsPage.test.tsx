import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes, useLocation } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EventGridCard } from '@/components/content/EventGridCard'
import type { CountedPage, EventCategory, EventSummary } from '@/lib/api'
import { renderWithProviders } from '@/test/render'
import { EventsPage, PAGE_SIZE } from './EventsPage'

const apiMock = vi.hoisted(() => ({ events: vi.fn(), eventCalendar: vi.fn(), featuredEvent: vi.fn() }))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return { ...actual, api: { ...actual.api, ...apiMock } }
})
vi.mock('@/lib/pageContent', () => ({
  usePageContent: () => ({ status: 'success', retry: () => undefined, entry: () => null, text: () => '', items: () => [] }),
}))

function makeEvent(n: number, extra: Partial<EventSummary> = {}): EventSummary {
  return {
    id: n,
    slug: `evening-${n}`,
    title: `Evening ${n}`,
    summary: `What happens on evening ${n}.`,
    category: 'social',
    category_label: 'Social',
    audience: 'public',
    starts_at: '2026-11-06T21:00:00-06:00',
    ends_at: '2026-11-06T23:00:00-06:00',
    timing: 'upcoming',
    location_label: '',
    hero_image: null,
    image_fallback: 'social',
    rsvp: { state: 'open', can_rsvp: true, reason: 'ok', opens_at: null, closes_at: '2026-11-06T21:00:00-06:00', max_party_size: 2, plan_party_limit: null, events_remaining: null, mine: null },
    attendee_count: null,
    ...extra,
  }
}

/** The server's pages of `total` events, 15 at a time. */
function serve(total: number) {
  apiMock.events.mockImplementation(async (category: EventCategory | '', page = 1): Promise<CountedPage<EventSummary>> => {
    const all = Array.from({ length: total }, (_, index) => makeEvent(index + 1, category ? { category } : {}))
    const results = all.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
    return { count: total, next: page * PAGE_SIZE < total ? `?page=${page + 1}` : null, previous: null, results }
  })
}

function Where() {
  const location = useLocation()
  return <p data-testid="where">{location.search}</p>
}

function renderEvents(path = '/events') {
  renderWithProviders(
    <>
      <Routes>
        <Route path="/events" element={<EventsPage />} />
      </Routes>
      <Where />
    </>,
    { path },
  )
}

function cards() {
  return screen.getAllByRole('article')
}

beforeEach(() => {
  apiMock.events.mockReset()
  apiMock.eventCalendar.mockReset()
  apiMock.featuredEvent.mockReset().mockResolvedValue({ event: null })
})

describe('the Events grid', () => {
  it('shows 15 at a time, with the count, and Load more adds the next 15 and moves the URL on', async () => {
    serve(20)
    renderEvents()
    expect(await screen.findByText('Showing 1–15 of 20')).toBeInTheDocument()
    expect(cards()).toHaveLength(15)
    const views = screen.getByRole('group', { name: 'View' })
    expect(within(views).getAllByRole('button').map((button) => button.textContent)).toEqual(['Grid', 'Month'])
    expect(within(views).getByRole('button', { name: 'Grid' })).toHaveAttribute('aria-pressed', 'true')

    await userEvent.click(screen.getByRole('button', { name: 'Load more' }))
    expect(await screen.findByText('Showing 1–20 of 20')).toBeInTheDocument()
    expect(cards()).toHaveLength(20)
    expect(screen.getByTestId('where')).toHaveTextContent('?page=2')
    expect(apiMock.events).toHaveBeenLastCalledWith('', 2)
    expect(apiMock.events).toHaveBeenCalledTimes(2)
    expect(screen.queryByRole('button', { name: 'Load more' })).not.toBeInTheDocument()
    // The first card of the new page has focus.
    expect(within(cards()[15]).getByRole('link')).toHaveFocus()
  })

  it('shows only the pages the URL asks for, without fetching again', async () => {
    serve(40)
    renderEvents('/events?page=2')
    expect(await screen.findByText('Showing 1–30 of 40')).toBeInTheDocument()
    await userEvent.click(within(screen.getByRole('navigation', { name: 'Pages' })).getByRole('link', { name: 'Page 1' }))
    expect(await screen.findByText('Showing 1–15 of 40')).toBeInTheDocument()
    expect(cards()).toHaveLength(15)
    expect(apiMock.events).toHaveBeenCalledTimes(2)
  })

  it('opens a shared ?page=2 link with both pages, and lists the pages as links', async () => {
    serve(40)
    renderEvents('/events?page=2')
    expect(await screen.findByText('Showing 1–30 of 40')).toBeInTheDocument()
    const pages = screen.getByRole('navigation', { name: 'Pages' })
    expect(within(pages).getAllByRole('link').map((link) => link.textContent)).toEqual(['1', '2', '3'])
    expect(within(pages).getByRole('link', { name: 'Page 2' })).toHaveAttribute('aria-current', 'page')
    expect(within(pages).getByRole('link', { name: 'Page 3' })).toHaveAttribute('href', '/events?page=3')
  })

  it('stops at the last page when a link asks for more', async () => {
    serve(20)
    renderEvents('/events?page=5')
    expect(await screen.findByText('Showing 1–20 of 20')).toBeInTheDocument()
    expect(apiMock.events).toHaveBeenCalledTimes(2)
  })

  it('goes back to page 1 when the category changes', async () => {
    serve(20)
    renderEvents('/events?page=2')
    expect(await screen.findByText('Showing 1–20 of 20')).toBeInTheDocument()
    await userEvent.click(within(screen.getByRole('group', { name: 'Category' })).getByRole('button', { name: 'Workshops' }))
    expect(await screen.findByTestId('where')).toHaveTextContent('?category=workshop')
    expect(screen.getByTestId('where')).not.toHaveTextContent('page=')
    expect(apiMock.events).toHaveBeenLastCalledWith('workshop', 1)
    expect(await screen.findByText('Showing 1–15 of 20')).toBeInTheDocument()
  })

  it('says so when nothing is scheduled', async () => {
    serve(0)
    renderEvents()
    expect(await screen.findByText('Nothing scheduled yet')).toBeInTheDocument()
    expect(screen.queryByText(/Showing/)).not.toBeInTheDocument()
  })
})

describe('the featured event', () => {
  const star = makeEvent(99, { title: 'Winter ball', category: 'special', category_label: 'Special', summary: 'One night a year.' })

  it('shows at the top, above the filters and the grid, with a way in', async () => {
    serve(20)
    apiMock.featuredEvent.mockImplementation(async (category: EventCategory | '') => ({ event: !category || category === 'special' ? star : null }))
    renderEvents()
    const banner = await screen.findByRole('article', { name: 'Winter ball' })
    expect(within(banner).getByText('Featured')).toBeInTheDocument()
    expect(within(banner).getByText('One night a year.')).toHaveClass('line-clamp-3')
    expect(within(banner).getByRole('link', { name: 'View event: Winter ball' })).toHaveAttribute('href', '/events/evening-99')
    const filters = screen.getByRole('group', { name: 'Category' })
    expect(banner.compareDocumentPosition(filters) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    // The grid's 15 come from the list, which leaves the featured event out (the server's job).
    expect(await screen.findByText('Showing 1–15 of 20')).toBeInTheDocument()
    expect(screen.getAllByRole('article', { name: 'Winter ball' })).toHaveLength(1)
  })

  it('arrives with the filters and the events on the first load, so nothing on screen is pushed down', async () => {
    serve(20)
    let answer: (value: { event: EventSummary | null }) => void = () => {}
    apiMock.featuredEvent.mockReturnValue(new Promise((resolve) => (answer = resolve)))
    renderEvents()
    // The events load meanwhile, but nothing below the title shows until the banner is known.
    expect(await screen.findByText('Showing 1–15 of 20')).not.toBeVisible()
    expect(screen.queryByRole('group', { name: 'Category' })).not.toBeInTheDocument()
    answer({ event: star })
    const banner = await screen.findByRole('article', { name: 'Winter ball' })
    expect(banner.compareDocumentPosition(screen.getByRole('group', { name: 'Category' })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(await screen.findByText('Showing 1–15 of 20')).toBeVisible()
  })

  it('goes when a category leaves it out', async () => {
    serve(20)
    apiMock.featuredEvent.mockImplementation(async (category: EventCategory | '') => ({ event: !category || category === 'special' ? star : null }))
    renderEvents()
    expect(await screen.findByRole('article', { name: 'Winter ball' })).toBeInTheDocument()
    await userEvent.click(within(screen.getByRole('group', { name: 'Category' })).getByRole('button', { name: 'Workshops' }))
    expect(apiMock.featuredEvent).toHaveBeenLastCalledWith('workshop')
    await screen.findByText('Showing 1–15 of 20')
    expect(screen.queryByRole('article', { name: 'Winter ball' })).not.toBeInTheDocument()
  })
})

describe('an Events grid card', () => {
  function renderCard(event: EventSummary, priority = false) {
    renderWithProviders(<EventGridCard event={event} priority={priority} />)
    return screen.getByRole('article')
  }

  it('shows the picture with its sizes, the date, the category and time, the title, summary and status', () => {
    const card = renderCard(
      makeEvent(1, {
        title: 'Spring social',
        hero_image: { url: '/media/events/a.webp', alt: 'The hall, lit', width: 1600, height: 1200, srcset: '/media/events/a-400w.webp 400w, /media/events/a.webp 1600w' },
      }),
      true,
    )
    const image = within(card).getByRole('img', { name: 'The hall, lit' })
    expect(image).toHaveAttribute('srcset', '/media/events/a-400w.webp 400w, /media/events/a.webp 1600w')
    expect(image).toHaveAttribute('sizes', expect.stringContaining('(min-width: 1024px) 31vw'))
    expect(image).toHaveAttribute('width', '1600')
    expect(image).toHaveAttribute('height', '1200')
    expect(image).toHaveAttribute('loading', 'eager')
    expect(within(card).getByText('Social')).toBeInTheDocument()
    expect(within(card).getByText(/9:00.*11:00 PM/)).toBeInTheDocument()
    expect(within(card).getByRole('link', { name: 'Spring social' })).toHaveAttribute('href', '/events/evening-1')
    expect(within(card).getByRole('heading', { name: 'Spring social' })).toHaveClass('line-clamp-2')
    expect(within(card).getByText('What happens on evening 1.')).toHaveClass('line-clamp-2')
    expect(within(card).getByText('Open')).toBeInTheDocument()
    expect(within(card).getByText('Nov')).toBeInTheDocument()
  })

  it('lazy-loads pictures after the first row', () => {
    const card = renderCard(makeEvent(1, { hero_image: { url: '/m/a.webp', alt: 'A', width: 800, height: 600, srcset: null } }))
    expect(within(card).getByRole('img')).toHaveAttribute('loading', 'lazy')
  })

  it("stands in the category's picture when there is none, never an empty box", () => {
    const card = renderCard(makeEvent(1, { category: 'workshop', image_fallback: 'workshop' }))
    expect(within(card).queryByRole('img')).not.toBeInTheDocument()
    expect(card.querySelector('[data-fallback="workshop"]')).not.toBeNull()
  })

  it('marks members-only evenings over the picture', () => {
    const card = renderCard(makeEvent(1, { audience: 'members' }))
    expect(within(card).getByText('Members only')).toBeInTheDocument()
  })
})

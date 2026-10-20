import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ClubPost, FeedPath, FeedTeaser, PathStep } from '@/lib/membersApi'
import { renderWithProviders, verifiedUser } from '@/test/render'
import { CommunityTeaser } from './CommunityTeaser'
import { WhatsMissing } from './WhatsMissing'

const account = vi.hoisted(() => ({ resendVerification: vi.fn() }))
const feed = vi.hoisted(() => ({ teaser: vi.fn() }))
const members = vi.hoisted(() => ({ me: vi.fn(), feed: vi.fn(), profile: vi.fn(), directory: vi.fn() }))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return { ...actual, api: { ...actual.api, ...account } }
})
vi.mock('@/lib/membersApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membersApi')>()
  return {
    ...actual,
    feedAccount: { ...actual.feedAccount, ...feed },
    members: { ...actual.members, ...members },
  }
})

beforeEach(() => {
  account.resendVerification.mockReset().mockResolvedValue(undefined)
  feed.teaser.mockReset()
  for (const fn of Object.values(members)) fn.mockReset()
})

const ORDER: PathStep['key'][] = ['email', 'plan', 'door', 'age', 'join']

function pathAt(at: PathStep['key'] | 'complete', changes: Partial<Record<PathStep['key'], object>> = {}, keys = ORDER): FeedPath {
  const reached = at === 'complete' ? keys.length : keys.indexOf(at)
  const state = (key: PathStep['key']) => {
    const index = keys.indexOf(key)
    return index < reached ? 'done' : index === reached ? 'current' : 'upcoming'
  }
  const all: Record<PathStep['key'], object> = {
    email: {},
    plan: { included: false, tier: null },
    door: { included: false, reference_code: null, waiting_for: null },
    age: { notice: false },
    join: { paused: false, can_join: at === 'join', early: false },
  }
  const steps = keys.map((key) => ({ key, state: state(key), ...all[key], ...changes[key] })) as PathStep[]
  return { steps, complete: at === 'complete' }
}

function showPath(path: FeedPath) {
  renderWithProviders(<WhatsMissing path={path} displayName="night_owl" cardShowsCode={false} />, { user: verifiedUser })
  return screen.getByRole('list')
}

/** Each step's title and where it stands: "Done", "Next", "Paused" or "Not yet". */
function rows(list: HTMLElement) {
  return within(list)
    .getAllByRole('listitem')
    .map((item) => Array.from(item.querySelectorAll('p:first-child > span'), (span) => span.textContent))
}

describe("What's missing", () => {
  it('lists the steps in order, with the email first for a new account', async () => {
    const list = showPath(pathAt('email'))
    expect(screen.getByRole('heading', { name: "What's missing" })).toBeInTheDocument()
    expect(rows(list)).toEqual([
      ['Verify email', 'Next'],
      ['Choose a plan', 'Not yet'],
      ['Get activated at the door', 'Not yet'],
      ['Age check', 'Not yet'],
      ['Join the community', 'Not yet'],
    ])
    expect(within(list).getAllByRole('listitem')[0]).toHaveAttribute('aria-current', 'step')
    await userEvent.click(screen.getByRole('button', { name: 'Send a new link' }))
    expect(account.resendVerification).toHaveBeenCalled()
    expect(await screen.findByText('A new link is on its way.')).toHaveAttribute('role', 'status')
    expect(screen.queryByRole('link', { name: 'Compare plans' })).not.toBeInTheDocument()
  })

  it('asks for a plan, naming one that leaves the community out', () => {
    const list = showPath(pathAt('plan', { plan: { tier: 'Community' } }))
    expect(rows(list).slice(0, 2)).toEqual([
      ['Verify email', 'Done'],
      ['Choose a plan', 'Next'],
    ])
    expect(screen.getByText('Your plan, Community, leaves out the member community.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Compare plans' })).toHaveAttribute('href', '/membership')
  })

  it.each([
    ['payment', 'Pay at the front desk and staff switch your membership on. Show them your code.'],
    ['id_check', 'Already paid. Staff switch your membership on at your next visit. Show them your code.'],
  ] as const)('sends them to the door with their reference code (waiting for %s)', async (waiting, text) => {
    showPath(pathAt('door', { door: { reference_code: 'R7K-42Q', waiting_for: waiting } }))
    expect(screen.getByText(text)).toBeInTheDocument()
    expect(await screen.findByAltText('QR code for R7K-42Q')).toBeInTheDocument()
    // The code is there, so the age step does not ask for the display name.
    expect(screen.queryByText(/give your display name/)).not.toBeInTheDocument()
  })

  it('says a suspended membership is on hold, with no code to show', () => {
    showPath(pathAt('door', { door: { reference_code: 'R7K-42Q', waiting_for: 'suspended' } }))
    expect(screen.getByText('Your membership is on hold. Ask at the front desk.')).toBeInTheDocument()
    expect(screen.queryByText('R7K-42Q')).not.toBeInTheDocument()
  })

  it('explains the age check, and that nothing is stored', () => {
    const list = showPath(pathAt('age', { plan: { included: true }, door: { included: true } }))
    expect(rows(list)[3]).toEqual(['Age check', 'Next'])
    expect(screen.getByText(/Bring a valid photo ID showing you are 18 or older/)).toBeInTheDocument()
    expect(screen.getByText(/We never copy or store your ID/)).toBeInTheDocument()
    expect(screen.getByText(/At the door, give your display name/)).toHaveTextContent('night_owl')
    expect(screen.getAllByText('Included with your account.')).toHaveLength(2)
  })

  it('points to the membership card for the door code once the membership is on', () => {
    renderWithProviders(<WhatsMissing path={pathAt('age')} displayName="night_owl" cardShowsCode />, { user: verifiedUser })
    expect(screen.getByText('At the door, show the code on your membership card.')).toBeInTheDocument()
    expect(screen.queryByText(/give your display name/)).not.toBeInTheDocument()
  })

  it('has no age step while the club has the check switched off', () => {
    const list = showPath(pathAt('join', {}, ['email', 'plan', 'door', 'join']))
    expect(rows(list).map(([title]) => title)).toEqual(['Verify email', 'Choose a plan', 'Get activated at the door', 'Join the community'])
    expect(screen.queryByText('Age check')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Join the community' })).toHaveAttribute('href', '/members/join-feed')
  })

  it('says a paused account is paused, with no way to join', () => {
    const list = showPath(pathAt('join', { join: { paused: true, can_join: false } }))
    expect(rows(list)[4]).toEqual(['Join the community', 'Paused'])
    expect(screen.getByText('Your community access is paused. It reopens when the pause ends.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Join the community' })).not.toBeInTheDocument()
  })

  it('opens the community once every step is done', () => {
    const list = showPath(pathAt('complete'))
    expect(rows(list).every(([, chip]) => chip === 'Done')).toBe(true)
    expect(screen.getByText('Nothing. The member community is open to you.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open the community' })).toHaveAttribute('href', '/members/feed')
  })
})

const clubPost: ClubPost = {
  kind: 'club',
  id: 'club-spring-social',
  slug: 'spring-social',
  author: { handle: 'Rose', avatar: null },
  caption_html: 'Spring social photos from the club',
  posted: { recent: true, at: '2026-10-18T20:00:00Z', month: null },
  images: [{ id: 'spring-social-0', url: 'https://cdn.example/journal/a.jpg', srcset: null, alt: 'The hall', width: 1080, height: 1080 }],
  link: { label: 'Read on the website', url: '/journal/spring-social' },
}

const teaser: FeedTeaser = {
  tiles: [
    { kind: 'photo', image: { url: 'https://cdn.example/journal/a.jpg', srcset: null, alt: 'The hall', width: 1080, height: 1080 } },
    { kind: 'note', title: 'New class on Thursday' },
  ],
  post: clubPost,
}

describe('The member community preview', () => {
  it("shows the club's own posts, blurred, with the way to a plan", async () => {
    feed.teaser.mockResolvedValue(teaser)
    renderWithProviders(<CommunityTeaser showPlans />, { user: verifiedUser })
    const post = await screen.findByRole('article', { name: 'Post by Rose' })
    expect(within(post).getByText('Spring social photos from the club')).toBeInTheDocument()
    expect(within(post).getByRole('link', { name: /Read on the website/ })).toHaveAttribute('href', '/journal/spring-social')
    // The grid is decorative: nine squares, hidden from screen readers.
    const grid = screen.getByText('New class on Thursday').closest('ul')!
    expect(grid).toHaveAttribute('aria-hidden', 'true')
    expect(grid.children).toHaveLength(9)
    expect(grid.querySelector('img')).toHaveAttribute('src', 'https://cdn.example/journal/a.jpg')
    expect(screen.getByText('Members share photos, plans and conversation here')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'See plans' })).toHaveAttribute('href', '/membership')
    // Nothing from the member feed is asked for.
    for (const fn of Object.values(members)) expect(fn).not.toHaveBeenCalled()
  })

  it('leaves the plans button out once a plan with the community is chosen', async () => {
    feed.teaser.mockResolvedValue({ tiles: [], post: null })
    renderWithProviders(<CommunityTeaser showPlans={false} />, { user: verifiedUser })
    expect(await screen.findByText('Members share photos, plans and conversation here')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'See plans' })).not.toBeInTheDocument()
    expect(screen.queryByRole('article')).not.toBeInTheDocument()
  })
})

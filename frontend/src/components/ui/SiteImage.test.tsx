import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const request = vi.hoisted(() => vi.fn())

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return { ...actual, request }
})

const IMAGES = {
  'home.hero': {
    url: '/media/site-images/dance-floor.webp',
    alt: 'People dancing under stage lights',
    width: 1920,
    height: 1280,
    srcset: '/media/site-images/dance-floor-640w.webp 640w, /media/site-images/dance-floor.webp 1920w',
    focal: { x: 0.3, y: 0.6 },
  },
}

function writeIntoPage(images: object) {
  const data = document.createElement('script')
  data.type = 'application/json'
  data.id = 'rose-site-images'
  data.textContent = JSON.stringify(images)
  document.head.appendChild(data)
}

/** The module reads the page once, when first imported. */
async function load() {
  vi.resetModules()
  return (await import('./SiteImage')).SiteImage
}

afterEach(() => {
  document.getElementById('rose-site-images')?.remove()
  request.mockReset()
})

describe('SiteImage', () => {
  it('shows the slot the server wrote into the page, without a request', async () => {
    writeIntoPage(IMAGES)
    const SiteImage = await load()
    render(<SiteImage slot="home.hero" priority sizes="50vw" />)
    const image = screen.getByRole('img', { name: 'People dancing under stage lights' })
    expect(image).toHaveAttribute('src', IMAGES['home.hero'].url)
    expect(image).toHaveAttribute('srcset', IMAGES['home.hero'].srcset)
    expect(image).toHaveAttribute('loading', 'eager')
    expect(image).toHaveStyle({ objectPosition: '30% 60%' })
    expect(request).not.toHaveBeenCalled()
  })

  it('fetches every slot once when the page has none', async () => {
    request.mockResolvedValue({ images: IMAGES })
    const SiteImage = await load()
    render(
      <>
        <SiteImage slot="home.hero" />
        <SiteImage slot="about.hero" />
      </>,
    )
    expect(await screen.findByRole('img', { name: 'People dancing under stage lights' })).toBeInTheDocument()
    expect(request).toHaveBeenCalledTimes(1)
    expect(request).toHaveBeenCalledWith('/site-images/')
  })

  it('shows the texture for an empty or withheld slot', async () => {
    writeIntoPage({})
    const SiteImage = await load()
    const { container } = render(<SiteImage slot="about.hero" placeholder="warm" />)
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('.wash-warm')).not.toBeNull()
  })

  it('keeps the texture when the slots cannot be loaded', async () => {
    request.mockRejectedValue(new Error('offline'))
    const SiteImage = await load()
    const { container } = render(<SiteImage slot="home.hero" />)
    await waitFor(() => expect(request).toHaveBeenCalled())
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('.wash-rose')).not.toBeNull()
  })
})

import { describe, expect, it } from 'vitest'

// Every component and page, as text. Page pictures come from Admin > Page images through
// SiteImage; only the brand assets (the logo and its emblem) are files in the code.
const sources = import.meta.glob<string>(['/src/**/*.{ts,tsx}', '!/src/**/*.test.{ts,tsx}', '!/src/components/brand/**', '!/src/test/**'], {
  query: '?raw',
  import: 'default',
  eager: true,
})

const IMAGE_PATH = /["'`(][^"'`()\s]*\.(?:webp|jpe?g|png|avif|gif|svg)["'`)]|\/images\//

describe('page images', () => {
  it('reads the code it checks', () => {
    expect(Object.keys(sources).length).toBeGreaterThan(50)
  })

  it.each(Object.entries(sources))('%s names no image file', (_, source) => {
    // A name given to a file being uploaded (FormData) is not a picture on a page.
    const lines = source.split('\n').filter((line) => !line.includes('.append('))
    expect(lines.filter((line) => IMAGE_PATH.test(line))).toEqual([])
  })

  it('renders every page picture through SiteImage', () => {
    const slots = Object.values(sources).flatMap((source) => [...source.matchAll(/<(?:SiteImage|PageHero)\b[^>]*\bslot="([a-z]+\.[a-z_]+)"/g)].map((match) => match[1]))
    expect(slots.sort()).toEqual(['about.hero', 'donate.hero', 'guests.hero', 'home.hero', 'rentals.hero', 'visit.hero', 'volunteer.hero'])
  })
})

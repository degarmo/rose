/**
 * Screenshots the Rose design files into docs/design/reference/.
 *
 * Serves docs/design/source/ on a local port (the files load each other with fetch, which
 * file:// does not allow), opens each .dc.html in Chromium, waits for it to render, and
 * saves every element with a data-screen-label, named from the label and prefixed with
 * the file it came from. It also saves the whole design-system page and the post card.
 *
 * The design files load React and Google Fonts from public CDNs to render; that is fine
 * for viewing the designs. The app itself makes no third-party requests.
 *
 *   node e2e/scripts/capture-design-reference.mjs
 *
 * CHROMIUM_PATH picks a Chromium build; without it the installed Chrome is used.
 */
import { createServer } from 'node:http'
import { mkdir, readFile, rm } from 'node:fs/promises'
import { extname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const root = resolve(fileURLToPath(new URL('../../docs/design/', import.meta.url)))
const source = join(root, 'source')
const out = join(root, 'reference')

const FILES = [
  { file: 'Rose Design System.dc.html', prefix: 'system', full: 'design-system-page' },
  { file: 'Rose Public Site.dc.html', prefix: 'site' },
  { file: 'Rose Member App.dc.html', prefix: 'app' },
  { file: 'Post Card.dc.html', prefix: 'post-card', full: 'post-card', width: 470 },
]

const TYPES = { '.html': 'text/html', '.js': 'text/javascript' }

export function slug(label) {
  return label
    .toLowerCase()
    .replace(/&/g, ' ')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

const server = createServer(async (request, response) => {
  try {
    const path = join(source, decodeURIComponent(new URL(request.url, 'http://x').pathname))
    if (!path.startsWith(source)) throw new Error('outside')
    const body = await readFile(path)
    response.writeHead(200, { 'content-type': TYPES[extname(path)] ?? 'application/octet-stream' })
    response.end(body)
  } catch {
    response.writeHead(404).end()
  }
})
await new Promise((done) => server.listen(0, '127.0.0.1', done))
const base = `http://127.0.0.1:${server.address().port}/`

await rm(out, { recursive: true, force: true })
await mkdir(out, { recursive: true })
const browser = await chromium.launch(
  process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : { channel: 'chrome' },
)
const saved = []
try {
  for (const { file, prefix, full, width } of FILES) {
    const page = await browser.newPage({ viewport: { width: width ?? 1920, height: 1080 } })
    await page.goto(base + encodeURIComponent(file), { waitUntil: 'networkidle' })
    // Rendered once the custom element has replaced its template with real content.
    await page.waitForFunction(() => document.body.innerText.trim().length > 0 && !document.querySelector('sc-for, sc-if'), null, { timeout: 60_000 }).catch(() => {})
    await page.evaluate(() => document.fonts.ready)
    await page.waitForTimeout(500)
    for (const element of await page.locator('[data-screen-label]').all()) {
      const label = await element.getAttribute('data-screen-label')
      const name = `${prefix}--${slug(label)}.png`
      await element.screenshot({ path: join(out, name), animations: 'disabled' })
      saved.push(`${name}\t${label}`)
    }
    if (full) {
      await page.screenshot({ path: join(out, `${full}.png`), fullPage: true, animations: 'disabled' })
      saved.push(`${full}.png\t(whole page)`)
    }
    await page.close()
  }
} finally {
  await browser.close()
  server.close()
}
console.log(saved.join('\n'))
console.log(`${saved.length} images in ${out}`)

import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import type { Page } from '@playwright/test'
import { expect, seriousA11yViolations } from './support'

type Info = { project: { name: string } }

/** Phone screenshots are 390 wide; desktop ones are taken at 1440x900. */
export function shotWidth(info: Info) {
  return info.project.name === 'phone' ? 390 : 1440
}

export async function useShotViewport(page: Page, info: Info) {
  if (info.project.name === 'desktop') await page.setViewportSize({ width: 1440, height: 900 })
}

/** Scroll through the page so lazy images load, then wait until every image has finished. */
export async function loadAllImages(page: Page) {
  await page.evaluate(async () => {
    for (let y = 0; y < document.documentElement.scrollHeight; y += window.innerHeight / 2) {
      window.scrollTo(0, y)
      await new Promise((resolve) => setTimeout(resolve, 60))
    }
    window.scrollTo(0, 0)
  })
  await page.waitForFunction(() => [...document.images].every((image) => image.complete), undefined, { timeout: 15_000 })
}

async function settle(page: Page) {
  await page.waitForLoadState('load')
  await page.evaluate(() => document.fonts.ready)
  // Every image showing on screen has loaded; hidden or off-screen lazy ones may still wait.
  await page.waitForFunction(
    () =>
      [...document.images].every((image) => {
        const box = image.getBoundingClientRect()
        const onScreen =
          box.width > 0 && box.bottom > 0 && box.top < window.innerHeight && box.right > 0 && box.left < window.innerWidth
        return image.complete || !onScreen
      }),
    undefined,
    { timeout: 15_000 },
  )
  await page.waitForTimeout(400)
}

/**
 * Screenshots into docs/screenshots/<folder>/, after checking the page does not scroll
 * sideways and has no serious or critical axe findings.
 */
export function screenshotFolder(folder: string) {
  const out = fileURLToPath(new URL(`../../docs/screenshots/${folder}/`, import.meta.url))
  mkdirSync(out, { recursive: true })
  return async function snap(page: Page, name: string, info: Info, fullPage = false) {
    // Park the pointer in an empty corner, so no hover state shows.
    if (info.project.name === 'desktop') await page.mouse.move(1439, 899)
    if (fullPage) await loadAllImages(page)
    await settle(page)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    expect(await seriousA11yViolations(page), name).toEqual([])
    await page.screenshot({ path: `${out}${name}-${shotWidth(info)}.png`, fullPage })
  }
}

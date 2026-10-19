import { expect, test } from './support'

const EXIT = /^https:\/\/www\.weather\.gov\//

test.describe('Age gate and quick exit @smoke', () => {
  test.beforeEach(async ({ page }) => {
    // The exit destination is answered locally: tests never reach a real outside site.
    await page.route(EXIT, (route) => route.fulfill({ contentType: 'text/html', body: '<title>Weather</title>' }))
  })

  test('accepting shows the site and is remembered', async ({ page }) => {
    await page.goto('/')
    const gate = page.getByRole('dialog').or(page.locator('[aria-labelledby="age-gate-title"]'))
    await expect(gate.first()).toBeVisible()
    await expect(page.getByRole('navigation', { name: 'Main' })).toHaveCount(0)
    await page.getByRole('button', { name: "I'm 18 or older" }).click()
    await expect(page.getByRole('link', { name: 'Skip to content' })).toBeAttached()
    await page.reload()
    await expect(page.getByRole('button', { name: "I'm 18 or older" })).toHaveCount(0)
  })

  test('declining leaves without a trace of the site', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Leave', exact: true }).click()
    await expect(page).toHaveURL(/\/exit$/)
    await expect(page.getByText('This page is not available.')).toBeVisible()
    await expect(page).toHaveTitle(/^(?!.*Rose).*$/)
  })

  test('the Leave button exits and replaces history', async ({ page, baseURL }) => {
    await page.goto('/')
    await page.getByRole('button', { name: "I'm 18 or older" }).click()
    await page.goto('/events')
    await page.getByRole('link', { name: /Leave/ }).first().click()
    await expect(page).toHaveURL(EXIT)
    await page.goBack()
    await expect(page).not.toHaveURL(`${baseURL}/events`)
  })

  test('pressing Escape twice exits', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: "I'm 18 or older" }).click()
    await page.goto('/about')
    await page.keyboard.press('Escape')
    await page.keyboard.press('Escape')
    await expect(page).toHaveURL(EXIT)
  })

  test('one Escape does nothing', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: "I'm 18 or older" }).click()
    await page.keyboard.press('Escape')
    await page.waitForTimeout(1000)
    await expect(page).not.toHaveURL(EXIT)
  })
})

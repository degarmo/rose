import { confirmAge, expect, test } from './support'

async function fillContact(page: import('@playwright/test').Page, n: number) {
  await page.getByLabel('Name or display name').fill(`Test visitor ${n}`)
  await page.getByLabel('Email').fill(`visitor${n}@example.org`)
  await page.getByLabel('Topic').selectOption('general')
  await page.getByLabel('Message').fill('A question about visiting for the first time. Thank you!')
}

test.describe('Contact @smoke', () => {
  test('a message is sent, and repeated sending is limited', async ({ page, baseURL }) => {
    await confirmAge(page.context(), baseURL!)
    // The e2e stack allows three messages an hour from one address.
    for (let n = 1; n <= 3; n++) {
      await page.goto('/contact')
      await fillContact(page, n)
      await page.getByRole('button', { name: 'Send message' }).click()
      await expect(page.getByRole('heading', { name: 'Thank you. Your message is with us.' })).toBeVisible()
    }
    await page.goto('/contact')
    await fillContact(page, 4)
    await page.getByRole('button', { name: 'Send message' }).click()
    await expect(page.getByText('Too many messages')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Thank you. Your message is with us.' })).toHaveCount(0)
  })

  test('the bot trap field is out of sight and out of reach', async ({ page, baseURL }) => {
    await confirmAge(page.context(), baseURL!)
    await page.goto('/contact')
    const honeypot = page.locator('input[name="website"]')
    await expect(honeypot).toHaveAttribute('tabindex', '-1')
    await expect(page.locator('[aria-hidden="true"]:has(input[name="website"])')).toHaveCount(1)
    const box = await honeypot.boundingBox()
    expect(box!.x + box!.width).toBeLessThan(0) // positioned off-screen
    await expect(page.getByRole('textbox', { name: 'Website' })).toHaveCount(0)
  })
})

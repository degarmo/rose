import type { Page } from '@playwright/test'
import { deskAction, deskSearch, expect, mailLink, mailSubjects, personPage, staffLogin, test, uniqueEmail, uniqueName } from './support'

const PASSWORD = 'a-long-e2e-password-42'

/** A date string (YYYY-MM-DD) some days from now. */
function inDays(days: number) {
  return new Date(Date.now() + days * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
}

async function registerAndSignIn(page: Page, next: string) {
  const email = uniqueEmail('e2e.guest')
  const name = uniqueName('guest')
  await page.goto('/account/register')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Display name').fill(name)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Create account' }).click()
  const link = new URL(await mailLink(email, '/account/verify#token='))
  await page.goto(link.pathname + link.hash)
  await expect(page.getByText('Your email is confirmed.')).toBeVisible()
  await page.goto(`/account/login?next=${encodeURIComponent(next)}`)
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Log in' }).click()
  return { email, name }
}

test.describe('Guests', () => {
  test('sign up as a guest, then in for the night at the door desk', async ({ browser, baseURL }) => {
    const guest = await personPage(browser, baseURL!)
    const { name } = await registerAndSignIn(guest, '/guests')
    await expect(guest.getByRole('heading', { level: 1 })).toBeVisible()
    await guest.getByRole('link', { name: 'Sign up as a guest' }).click()

    // Straight to the agreement, then the in-person method only.
    const agreement = guest.getByRole('region', { name: 'Agreement text' })
    await agreement.evaluate((element) => element.scrollTo(0, element.scrollHeight))
    await guest.getByLabel('I have read the agreement and I agree to it.').check()
    await guest.getByLabel(/Type your full name to sign/).fill('Casey Guestperson')
    await guest.getByRole('button', { name: 'Agree and continue' }).click()
    await expect(guest.getByRole('radio')).toHaveCount(1)
    await guest.getByRole('button', { name: 'Get my reference code' }).click()
    await expect(guest.getByText('Your guest pass is ready')).toBeVisible()
    const code = (await guest.getByAltText(/QR code for/).getAttribute('alt'))!.replace('QR code for ', '')

    const desk = await personPage(browser, baseURL!)
    await staffLogin(desk)
    await deskSearch(desk, code)
    const card = desk.getByRole('article', { name })
    await expect(card.getByText('Guest pass')).toBeVisible()
    await deskAction(desk, name, 'Guest visit', 'Guest visit', 'Record payment, in for tonight')
    await expect(desk.getByText(`${code} is in for tonight.`)).toBeVisible()
    await expect(card.getByText('Convert to member')).toBeVisible()

    await guest.context().close()
    await desk.context().close()
  })
})

test.describe('Rentals', () => {
  test('a photoshoot inquiry needs the consent promise, then is received', async ({ page, baseURL }) => {
    await page.context().addCookies([{ name: 'age_ok', value: '1', url: baseURL!, sameSite: 'Strict' }])
    const email = uniqueEmail('e2e.rental')
    await page.goto('/rentals')
    const form = page.getByRole('form', { name: 'Rental inquiry' })
    await form.getByLabel('Name or display name').fill('Robin Planner')
    await form.getByLabel('Email').fill(email)
    await form.getByLabel('What is it for?').selectOption('photoshoot')
    await form.getByLabel('Preferred date').fill(inDays(21))
    await form.getByLabel('Start time').fill('14:00')
    await form.getByLabel('Hours').selectOption('3')
    await form.getByLabel('How many people').fill('4')
    await form.getByRole('button', { name: 'Send request' }).click()
    await expect(page.getByText('Photoshoots need this promise before we can talk dates.')).toBeVisible()
    await form.getByLabel(/Everyone photographed will consent/).check()
    await form.getByRole('button', { name: 'Send request' }).click()
    await expect(page.getByRole('heading', { name: 'Thank you. Your request is with us.' })).toBeVisible()
    await expect.poll(() => mailSubjects(email)).toContain('We received your request')
  })
})

test.describe('Donations', () => {
  test('give online through the sandbox checkout', async ({ page, baseURL }) => {
    await page.context().addCookies([{ name: 'age_ok', value: '1', url: baseURL!, sameSite: 'Strict' }])
    const email = uniqueEmail('e2e.giver')
    await page.goto('/get-involved/donate')
    const form = page.getByRole('form', { name: 'Give online' })
    await form.getByText('$25', { exact: true }).click()
    await form.getByLabel(/Email for an acknowledgement/).fill(email)
    await form.getByRole('button', { name: 'Give $25' }).click()

    await expect(page.getByRole('heading', { name: 'Test checkout' })).toBeVisible()
    await expect(page.getByText('Donation', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Pay', exact: true }).click()
    await expect(page).toHaveURL(/\/get-involved\/donate\?thanks=1$/)
    await expect(page.getByRole('heading', { name: 'Thank you for your gift.' })).toBeVisible()
    // The gift is recorded from the provider's webhook, which sends the acknowledgement.
    await expect.poll(() => mailSubjects(email), { timeout: 30_000 }).toContain('Thank you for your gift')
  })
})

test.describe('Email list', () => {
  test('subscribe, confirm by email, then leave in one click', async ({ page, baseURL }) => {
    await page.context().addCookies([{ name: 'age_ok', value: '1', url: baseURL!, sameSite: 'Strict' }])
    const email = uniqueEmail('e2e.reader')
    await page.goto('/')
    const signup = page.getByRole('form', { name: 'Stay in touch' })
    await signup.getByRole('textbox').fill(email)
    await signup.getByRole('button', { name: 'Sign up' }).click()
    await expect(signup.getByText('Check your inbox for a link to confirm.')).toBeVisible()

    const confirm = new URL(await mailLink(email, '/subscribe/confirm#token='))
    expect(await mailSubjects(email)).toEqual(['Please confirm your email'])
    await page.goto(confirm.pathname + confirm.hash)
    await expect(page.getByText('You are subscribed. Thank you.')).toBeVisible()
    // The token leaves the address bar once used.
    await expect(page).toHaveURL(/\/subscribe\/confirm$/)

    const token = new URLSearchParams(confirm.hash.slice(1)).get('token')!
    await page.goto(`/unsubscribe#token=${token}`)
    await page.getByRole('button', { name: 'Unsubscribe' }).click()
    await expect(page.getByText('You are unsubscribed. No more email will be sent.')).toBeVisible()
  })

  test('the one-click unsubscribe address changes nothing on a plain visit', async ({ page, baseURL }) => {
    await page.context().addCookies([{ name: 'age_ok', value: '1', url: baseURL!, sameSite: 'Strict' }])
    const response = await page.request.get('/api/newsletter/unsubscribe/not-a-real-token/', { maxRedirects: 0 })
    expect(response.status()).toBe(302)
    expect(response.headers()['location']).toMatch(/\/unsubscribe#token=not-a-real-token$/)
  })
})

test.describe('Old addresses', () => {
  test('the old gallery moves to the journal', async ({ page, baseURL }) => {
    await page.context().addCookies([{ name: 'age_ok', value: '1', url: baseURL!, sameSite: 'Strict' }])
    const response = await page.request.get('/gallery', { maxRedirects: 0 })
    expect(response.status()).toBe(301)
    expect(response.headers()['location']).toBe('/journal')
  })
})

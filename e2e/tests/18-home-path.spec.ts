import { execSync } from 'node:child_process'
import { expect, mailLink, personPage, test, uniqueEmail } from './support'

/** Runs a management command in the app container, with DEBUG on for that one process. */
const MANAGE = process.env.E2E_MANAGE_CMD ?? 'docker compose -f ../docker-compose.e2e.yml exec -T -e DJANGO_DEBUG=true app python manage.py'

test.describe('The way into the member app', () => {
  test('make_feed_member gives a new account the feed; it logs in through the emailed link and lands there', async ({ browser, baseURL }) => {
    const email = uniqueEmail('feed.member')
    const output = execSync(`${MANAGE} make_feed_member ${email}`, { encoding: 'utf8' })
    for (const line of ['Account: created', 'activated on Rose at the door desk by system_dev', 'Feed: joined', `a link to choose one was sent to ${email}`]) {
      expect(output).toContain(line)
    }

    // The link to choose a password, as it arrives in Mailpit.
    const link = new URL(await mailLink(email, '/account/reset#uid='))
    const page = await personPage(browser, baseURL!)
    await page.goto(link.pathname + link.hash)
    const password = 'feed-member-password-0123'
    await page.getByLabel('New password', { exact: true }).fill(password)
    await page.getByLabel('Type it again').fill(password)
    await page.getByRole('button', { name: 'Save new password' }).click()
    await expect(page.getByText('Your password has been changed.')).toBeVisible()
    await page.getByRole('main').getByRole('link', { name: 'Log in' }).click()

    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Log in' }).click()
    await expect(page).toHaveURL(/\/members\/feed$/)
    await expect(page.getByRole('navigation', { name: 'Members' }).first()).toBeVisible()

    // Home agrees: nothing is missing.
    await page.goto('/members/home')
    await expect(page.getByText('Nothing. The member community is open to you.')).toBeVisible()
    await expect(page.getByRole('link', { name: 'Open the community' })).toHaveAttribute('href', '/members/feed')
    await page.context().close()
  })
})

import { apiLogin, confirmAge, expect, fixtures, mailSubjects, personPage, test } from './support'

test.describe('Events and RSVPs', () => {
  test('RSVP to a public evening and cancel it', async ({ page, baseURL }, info) => {
    const data = fixtures().viewports[info.project.name]
    await confirmAge(page.context(), baseURL!)
    await apiLogin(page, baseURL!, data.feed.poster, fixtures().password)
    await page.goto(`/events/${data.events.open}`)
    const panel = page.getByRole('article', { name: 'RSVP' })
    await panel.getByRole('button', { name: 'RSVP', exact: true }).click()
    await expect(panel.getByText('You are going')).toBeVisible()
    await expect.poll(() => mailSubjects(data.feed.poster)).toContainEqual(expect.stringMatching(/^Your plans for /))

    await panel.getByRole('button', { name: 'Change or cancel' }).click()
    await panel.getByRole('button', { name: 'Cancel my RSVP' }).click()
    await page.getByRole('dialog', { name: 'Cancel your RSVP?' }).getByRole('button', { name: 'Yes, cancel' }).click()
    await expect(panel.getByRole('button', { name: 'RSVP', exact: true })).toBeVisible()
  })

  test('a waitlisted member is promoted when a place opens', async ({ browser, baseURL }, info) => {
    const data = fixtures().viewports[info.project.name]
    const slug = data.events.waitlist
    const first = await personPage(browser, baseURL!, data.feed.poster)
    const second = await personPage(browser, baseURL!, data.feed.friend)

    await first.goto(`/events/${slug}`)
    await first.getByRole('button', { name: 'RSVP', exact: true }).click()
    await expect(first.getByText('You are going')).toBeVisible()

    await second.goto(`/events/${slug}`)
    await second.getByRole('button', { name: 'Join the waitlist' }).click()
    await expect(second.getByText('You are on the waitlist').first()).toBeVisible()

    await first.getByRole('button', { name: 'Change or cancel' }).click()
    await first.getByRole('button', { name: 'Cancel my RSVP' }).click()
    await first.getByRole('dialog', { name: 'Cancel your RSVP?' }).getByRole('button', { name: 'Yes, cancel' }).click()

    await second.reload()
    await expect(second.getByText('You are going')).toBeVisible()
    await expect.poll(() => mailSubjects(data.feed.friend)).toContainEqual(expect.stringMatching(/^A place opened up for /))
    // Nobody else's name is ever on the page.
    await expect(second.getByText('e2e_' + info.project.name + '_poster')).toHaveCount(0)
    await first.context().close()
    await second.context().close()
  })

  test('members-only evenings ask non-members to join', async ({ page, baseURL }, info) => {
    const data = fixtures().viewports[info.project.name]
    await confirmAge(page.context(), baseURL!)
    await page.goto(`/events/${data.events.members}`)
    const panel = page.getByRole('article', { name: 'RSVP' })
    await expect(panel.getByRole('link', { name: 'Join to RSVP' })).toBeVisible()
    await expect(panel.getByRole('link', { name: 'Log in' })).toBeVisible()
    await expect(panel.getByRole('link', { name: 'Create an account' })).toHaveCount(0)

    await apiLogin(page, baseURL!, data.feed.friend, fixtures().password)
    await page.reload()
    await expect(panel.getByRole('link', { name: 'Join to RSVP' })).toBeVisible()
    await expect(panel.getByRole('link', { name: 'Log in' })).toHaveCount(0)
    await expect(page.getByRole('link', { name: 'Become a member' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'RSVP', exact: true })).toHaveCount(0)
  })
})

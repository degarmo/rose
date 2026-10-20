import type { Page } from '@playwright/test'
import { deskSearch, expect, fixtures, freshCode, personPage, staffLogin, test, twoStepLogin } from './support'

/** The admin's Members list, narrowed to these members, with them ticked and an action run. */
async function bulkAction(page: Page, handles: string[], action: string) {
  const data = fixtures()
  await page.goto(`${data.admin_path}accounts/user/?q=${handles[0].replace(/\d+$/, '')}`)
  for (const handle of handles) {
    await page.getByRole('row').filter({ hasText: handle }).getByRole('checkbox').check()
  }
  await page.locator('select[name="action"]').selectOption({ label: action })
  await page.getByRole('button', { name: /^(Run|Go)$/ }).click()
  await expect(page.getByRole('heading', { name: action, level: 1 })).toBeVisible()
  for (const handle of handles) await expect(page.getByRole('listitem').filter({ hasText: handle })).toBeVisible()
}

test.describe('The admin’s Members actions', () => {
  test('a moderator suspends three members from the feed and lifts it; an admin bans one and the door desk turns them away', async ({ browser, baseURL }, info) => {
    const data = fixtures()
    const subjects = data.viewports[info.project.name].user_actions
    const handles = subjects.map((subject) => subject.handle)

    // 1. A moderator ticks three members and suspends them from the feed for 7 days.
    const moderator = await personPage(browser, baseURL!)
    await twoStepLogin(moderator, data.team.moderator)
    await bulkAction(moderator, handles, 'Suspend from feed')
    await expect(moderator.getByLabel('7 days')).toBeChecked()
    await moderator.getByLabel('Rule broken').fill('Consent first')
    await moderator.getByLabel('Reason').fill('Photos shared without asking.')
    await moderator.getByRole('button', { name: 'Suspend from feed' }).click()
    await expect(moderator.getByText('Suspend from feed: done for 3')).toBeVisible()

    // 2. Each of them sees the notice in Settings, and the feed is closed to them.
    const members = []
    for (const subject of subjects) {
      const member = await personPage(browser, baseURL!, subject.email)
      await member.goto('/members/settings/notices')
      await expect(member.getByText('Feed suspension').first()).toBeVisible()
      expect((await member.request.get('/api/members/feed/')).status()).toBe(404)
      members.push(member)
    }

    // 3. The moderator lifts the suspensions, and the feed opens again.
    await bulkAction(moderator, handles, 'Lift suspensions')
    await moderator.getByLabel('Reason').fill('Talked it through at the social.')
    await moderator.getByRole('button', { name: 'Lift suspensions' }).click()
    await expect(moderator.getByText('Lift suspensions: done for 3')).toBeVisible()
    for (const member of members) expect((await member.request.get('/api/members/feed/')).status()).toBe(200)

    // 4. An admin bans one of them from their page, with a fresh code from the authenticator.
    const [banned] = subjects
    const admin = await personPage(browser, baseURL!)
    await twoStepLogin(admin, data.team.admin)
    await admin.goto(`${data.admin_path}accounts/user/?q=${banned.handle}`)
    await admin.getByRole('link', { name: banned.handle, exact: true }).click()
    const moderation = admin.locator('li[x-data*="actionDropdownOpen"] > a').filter({ hasText: 'Moderation' })
    // On a phone the action bar folds behind its "…" button.
    if (!(await moderation.isVisible())) await admin.locator('a').filter({ hasText: 'more_horiz' }).click()
    await moderation.click()
    await admin.getByRole('link', { name: 'Ban', exact: true }).click()
    await expect(admin.getByRole('heading', { name: 'Ban', level: 1 })).toBeVisible()
    await admin.getByLabel('Rule broken').fill('Consent first')
    await admin.getByLabel('Reason').fill('A third time, after the suspension.')
    await admin.getByLabel(/Six-digit code/).fill(await freshCode(data.team.admin.totp_secret))
    await admin.getByRole('button', { name: 'Ban', exact: true }).click()
    await expect(admin.getByText('Ban: done for 1')).toBeVisible()

    // 5. The door desk shows "Do not admit".
    const desk = await personPage(browser, baseURL!)
    await staffLogin(desk)
    await deskSearch(desk, banned.code)
    await expect(desk.getByRole('article', { name: banned.handle }).getByText(/Do not admit/)).toBeVisible()

    for (const page of [moderator, admin, desk, ...members]) await page.context().close()
  })
})

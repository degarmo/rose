import type { Page } from '@playwright/test'
import { allowedHosts, expect, fixtures, PHOTO, personPage, test } from './support'

async function joinFeedAgain(page: Page) {
  await page.getByRole('link', { name: 'Rejoin the feed' }).click()
  const readGuidelines = page.getByRole('button', { name: 'Read the guidelines' })
  const joinButton = page.getByRole('button', { name: 'Join the feed' })
  await expect(readGuidelines.or(joinButton)).toBeVisible()
  if (await readGuidelines.isVisible()) {
    await readGuidelines.click()
    await page
      .getByLabel('Community guidelines', { exact: true })
      .evaluate((element) => element.scrollTo(0, element.scrollHeight))
    await page.getByLabel('I agree to the community guidelines').check()
    await page.getByRole('button', { name: 'Continue' }).click()
  }
  await page.getByRole('button', { name: 'Join the feed' }).click()
  await page.getByRole('button', { name: 'Skip for now' }).click()
  await expect(page).toHaveURL(/\/members\/feed$/)
}

function postBy(page: Page, handle: string) {
  return page.getByRole('article', { name: `Post by ${handle}` })
}

test.describe('Member feed', () => {
  test('post, interact, report, block, step away, rejoin, leave and erase', async ({ browser, baseURL }, info) => {
    const data = fixtures().viewports[info.project.name]
    const posterHandle = `e2e_${info.project.name}_poster`
    // Both viewports' members share one feed, so every text names its viewport.
    const first = `Hello from the ${info.project.name} run`
    const second = `A second, text-only post (${info.project.name})`
    const comment = `Lovely colours (${info.project.name})`
    const poster = await personPage(browser, baseURL!, data.feed.poster)
    const friend = await personPage(browser, baseURL!, data.feed.friend)
    const offsite: string[] = []
    const allowed = allowedHosts(baseURL!)
    for (const page of [poster, friend]) {
      page.on('request', (request) => {
        const host = new URL(request.url()).host
        if (!allowed.has(host) && !request.url().startsWith('data:') && !request.url().startsWith('blob:')) {
          offsite.push(request.url())
        }
      })
    }

    // A photo post, with something covered before it ever leaves the device.
    await poster.goto('/members/feed')
    await poster.getByRole('button', { name: 'Create', exact: true }).click()
    await poster.locator('#composer-files').setInputFiles(PHOTO)
    await poster.getByRole('button', { name: 'Next', exact: true }).click()
    const surface = poster.getByTestId('redaction-surface')
    const box = (await surface.boundingBox())!
    await poster.mouse.move(box.x + box.width * 0.3, box.y + box.height * 0.3)
    await poster.mouse.down()
    await poster.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.6, { steps: 5 })
    await poster.mouse.up()
    await poster.getByRole('button', { name: 'Next', exact: true }).click()
    // Details: describe, caption, and the consent attestation.
    await poster.getByLabel('Describe photo 1').fill('Gold stripes on red')
    await poster.getByRole('textbox', { name: /^Caption/ }).fill(first)
    const share = poster.getByRole('button', { name: 'Share', exact: true })
    await expect(share).toBeDisabled() // consent first
    await poster.getByLabel(/Everyone identifiable in these photos agreed/).check()
    await share.click()
    await expect(poster.getByText('Your post has been shared.')).toBeVisible()
    await poster.keyboard.press('Escape')
    const mine = postBy(poster, posterHandle).filter({ hasText: first })
    await expect(mine).toBeVisible()

    // The image is served through the access-checked view, then a short signed URL.
    // Processing runs in the worker, so reload until it is done.
    const image = postBy(poster, posterHandle).filter({ hasText: first }).locator('img').first()
    await expect(async () => {
      await poster.reload()
      await expect(image).toBeVisible({ timeout: 2_000 })
    }).toPass({ timeout: 30_000 })
    await expect.poll(() => image.evaluate((element: HTMLImageElement) => element.naturalWidth)).toBeGreaterThan(0)

    // The friend likes and comments.
    await friend.goto('/members/feed')
    const seen = postBy(friend, posterHandle).filter({ hasText: first })
    await seen.getByRole('button', { name: /Like/ }).click()
    await expect(seen.getByRole('button', { name: /Like/ })).toHaveAttribute('aria-pressed', 'true')
    await seen.getByRole('textbox', { name: 'Add a comment' }).fill(comment)
    await seen.getByRole('button', { name: 'Post', exact: true }).click()
    await expect(seen.getByText(comment)).toBeVisible()
    await expect(seen.getByText('Liked by you')).toBeVisible()

    // The author sees the like count; nobody sees who liked it.
    await poster.goto('/members/feed')
    await expect(postBy(poster, posterHandle).first().getByText('1 like')).toBeVisible()

    // "Posted without consent" hides the post at once.
    await friend.goto('/members/feed')
    const reported = postBy(friend, posterHandle).filter({ hasText: first })
    await reported.getByRole('button', { name: 'Post options' }).click()
    await friend.getByRole('dialog', { name: 'Post options' }).getByRole('button', { name: 'Report to hosts' }).click()
    const dialog = friend.getByRole('dialog', { name: 'Report this post' })
    await dialog.getByLabel('Posted without consent').check()
    await dialog.getByRole('button', { name: 'Send report' }).click()
    await friend.reload()
    await expect(postBy(friend, posterHandle).filter({ hasText: first })).toHaveCount(0)
    await poster.reload()
    await expect(poster.getByText('Hidden while we review a report')).toBeVisible()

    // A text post, then the friend blocks the poster: it disappears for them.
    await poster.getByRole('button', { name: 'Create', exact: true }).click()
    await poster.getByRole('button', { name: 'Write a text post' }).click()
    await poster.getByRole('textbox', { name: /^Caption/ }).fill(second)
    await poster.getByRole('button', { name: 'Share', exact: true }).click()
    await expect(poster.getByText('Your post has been shared.')).toBeVisible()
    await poster.keyboard.press('Escape')
    await expect(postBy(poster, posterHandle).filter({ hasText: second })).toBeVisible()
    await friend.reload()
    const secondPost = postBy(friend, posterHandle).filter({ hasText: second })
    await secondPost.getByRole('button', { name: 'Post options' }).click()
    await friend.getByRole('dialog', { name: 'Post options' }).getByRole('button', { name: `Block ${posterHandle}` }).click()
    await friend.getByRole('dialog', { name: `Block ${posterHandle}?` }).getByRole('button', { name: 'Block' }).click()
    await friend.reload()
    await expect(postBy(friend, posterHandle)).toHaveCount(0)

    // Step away hides everything, rejoining brings it back.
    await poster.goto('/account')
    await poster.getByRole('button', { name: 'Step away from the feed' }).click()
    await poster.getByRole('dialog', { name: 'Step away from the feed?' }).getByRole('button', { name: 'Step away' }).click()
    await expect(poster.getByRole('link', { name: 'Rejoin the feed' })).toBeVisible()
    await joinFeedAgain(poster)
    await expect(postBy(poster, posterHandle).filter({ hasText: second })).toBeVisible()

    // Leave and erase, after typing the display name.
    await poster.goto('/account')
    await poster.getByRole('button', { name: 'Leave and erase' }).click()
    const erase = poster.getByRole('dialog', { name: 'Erase everything you shared?' })
    await expect(erase.getByRole('button', { name: 'Erase for good' })).toBeDisabled()
    await erase.getByLabel('Display name').fill(posterHandle)
    await erase.getByRole('button', { name: 'Erase for good' }).click()
    await expect(poster.getByText(/Erasing everything you shared/)).toBeVisible()
    await expect
      .poll(async () => (await poster.request.get('/api/account/feed/')).json().then((body) => body.has_content))
      .toBe(false)

    expect(offsite).toEqual([])
    await poster.context().close()
    await friend.context().close()
  })
})

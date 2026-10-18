import { defineConfig } from '@playwright/test'

/**
 * End-to-end tests at phone (390x844) and desktop widths, in the Chrome that is
 * already installed (locally and on CI runners). Nothing is downloaded.
 *
 * E2E_BASE_URL     the site (default: the docker-compose.e2e.yml stack)
 * E2E_BASIC_AUTH   "user:password" for a staging site behind basic auth
 * E2E_SMOKE=1      skip the fixture setup; run with --grep @smoke against staging
 */
const baseURL = process.env.E2E_BASE_URL ?? 'http://localhost:8080'
const [username, password] = (process.env.E2E_BASIC_AUTH ?? '').split(':')

export default defineConfig({
  testDir: 'tests',
  // One worker: the flows share one server, its rate limits and its mail outbox.
  workers: 1,
  fullyParallel: false,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  forbidOnly: Boolean(process.env.CI),
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  globalSetup: './global-setup.ts',
  use: {
    baseURL,
    channel: 'chrome',
    httpCredentials: username ? { username, password } : undefined,
    contextOptions: { reducedMotion: 'reduce' },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'phone',
      use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
    },
    { name: 'desktop', use: { viewport: { width: 1280, height: 800 } } },
  ],
})

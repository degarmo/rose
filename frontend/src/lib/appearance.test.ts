import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { verifiedUser } from '@/test/render'
import { adoptAccountAppearance, applyAppearance, chooseAppearance, cookieAppearance } from './appearance'

const api = vi.hoisted(() => ({ changeAppearance: vi.fn() }))
vi.mock('./api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api')>()
  return { ...actual, api: { ...actual.api, ...api } }
})

function clearCookie() {
  document.cookie = 'appearance=; Max-Age=0; Path=/'
}

beforeEach(() => {
  clearCookie()
  applyAppearance('light')
  api.changeAppearance.mockReset().mockResolvedValue({ user: { ...verifiedUser, appearance: 'dark' }, csrfToken: 't' })
})
afterEach(clearCookie)

describe('appearance', () => {
  it('is light by default, even when the device prefers dark', () => {
    const prefersDark = vi.spyOn(window, 'matchMedia').mockReturnValue({ matches: true } as MediaQueryList)
    expect(cookieAppearance()).toBe('light')
    applyAppearance(cookieAppearance())
    expect(document.documentElement.dataset.appearance).toBeUndefined()
    prefersDark.mockRestore()
  })

  it('remembers a choice in a cookie for visitors who are not signed in', async () => {
    await chooseAppearance('dark', false)
    expect(document.documentElement.dataset.appearance).toBe('dark')
    expect(document.cookie).toContain('appearance=dark')
    expect(cookieAppearance()).toBe('dark')
    expect(api.changeAppearance).not.toHaveBeenCalled()
  })

  it('saves the choice on the account when someone is signed in', async () => {
    const session = await chooseAppearance('dark', true)
    expect(api.changeAppearance).toHaveBeenCalledWith('dark')
    expect(session?.user?.appearance).toBe('dark')
  })

  it("follows the signed-in account's saved choice and remembers it for this browser", () => {
    adoptAccountAppearance({ ...verifiedUser, appearance: 'dark' })
    expect(document.documentElement.dataset.appearance).toBe('dark')
    expect(cookieAppearance()).toBe('dark')
    adoptAccountAppearance({ ...verifiedUser, appearance: 'light' })
    expect(document.documentElement.dataset.appearance).toBeUndefined()
    expect(cookieAppearance()).toBe('light')
  })
})

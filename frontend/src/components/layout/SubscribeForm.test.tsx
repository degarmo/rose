import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/lib/api'
import { renderWithProviders } from '@/test/render'
import { SubscribeForm } from './SubscribeForm'

const subscribe = vi.hoisted(() => vi.fn())

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return { ...actual, api: { ...actual.api, subscribe } }
})

const field = () => screen.getByRole('textbox', { name: /Occasional email/ })

beforeEach(() => {
  subscribe.mockReset()
})

describe('SubscribeForm', () => {
  it('checks the address before sending', async () => {
    renderWithProviders(<SubscribeForm />)
    await userEvent.type(field(), 'not-an-address')
    await userEvent.click(screen.getByRole('button', { name: 'Sign up' }))
    expect(screen.getByText('Enter a full email address, like name@example.com.')).toBeInTheDocument()
    expect(field()).toHaveAttribute('aria-invalid', 'true')
    expect(subscribe).not.toHaveBeenCalled()
  })

  it('shows the same check-your-inbox answer and clears the field', async () => {
    let resolve: (value: { detail: string }) => void = () => undefined
    subscribe.mockReturnValue(new Promise((r) => (resolve = r)))
    renderWithProviders(<SubscribeForm />)
    await userEvent.type(field(), 'reader@example.org')
    await userEvent.click(screen.getByRole('button', { name: 'Sign up' }))
    expect(screen.getByRole('button', { name: 'Sending' })).toBeDisabled()
    resolve({ detail: 'Check your inbox for a link to confirm.' })
    expect(await screen.findByText('Check your inbox for a link to confirm.')).toBeInTheDocument()
    expect(field()).toHaveValue('')
    expect(subscribe).toHaveBeenCalledWith('reader@example.org', '')
  })

  it('explains a rate limit in its own words', async () => {
    subscribe.mockImplementation(async () => {
      throw new ApiError(429, 'Slow down.')
    })
    renderWithProviders(<SubscribeForm />)
    await userEvent.type(field(), 'reader@example.org')
    await userEvent.click(screen.getByRole('button', { name: 'Sign up' }))
    expect(await screen.findByText('Too many attempts. Please try again later.')).toBeInTheDocument()
  })
})

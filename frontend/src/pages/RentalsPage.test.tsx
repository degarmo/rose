import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { chicagoDateKey } from '@/lib/format'
import { renderWithProviders, verifiedUser } from '@/test/render'
import { RentalInquiryForm } from './RentalsPage'
import { PHOTOSHOOT_PROMISE } from './rentalsValidation'

const send = vi.hoisted(() => vi.fn())

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return { ...actual, api: { ...actual.api, sendRentalInquiry: send } }
})

function inDays(days: number) {
  return chicagoDateKey(new Date(Date.now() + days * 24 * 60 * 60 * 1000))
}

async function fillValid() {
  await userEvent.type(screen.getByLabelText('Name or display name'), 'Robin Planner')
  await userEvent.type(screen.getByLabelText('Email'), 'robin@example.org')
  await userEvent.selectOptions(screen.getByLabelText('What is it for?'), 'workshop')
  await userEvent.type(screen.getByLabelText('Preferred date'), inDays(10))
  await userEvent.type(screen.getByLabelText('Start time'), '14:00')
  await userEvent.selectOptions(screen.getByLabelText('Hours'), '3')
  await userEvent.type(screen.getByLabelText('How many people'), '12')
}

beforeEach(() => {
  send.mockReset()
  send.mockResolvedValue({ detail: 'ok' })
})

describe('RentalInquiryForm', () => {
  it('shows every missing field and focuses the first', async () => {
    renderWithProviders(<RentalInquiryForm />)
    await userEvent.click(screen.getByRole('button', { name: 'Send request' }))
    expect(screen.getByText('Please tell us what to call you.')).toBeInTheDocument()
    expect(screen.getByText('We need an email address to reply.')).toBeInTheDocument()
    expect(screen.getByText('Choose what the space is for.')).toBeInTheDocument()
    expect(screen.getByText('Choose a date.')).toBeInTheDocument()
    expect(screen.getByText('Choose a start time.')).toBeInTheDocument()
    expect(screen.getByText('Choose how many hours.')).toBeInTheDocument()
    expect(screen.getByLabelText('Name or display name')).toHaveFocus()
    expect(send).not.toHaveBeenCalled()
  })

  it('refuses a date that is not in the future', async () => {
    renderWithProviders(<RentalInquiryForm />)
    await fillValid()
    const date = screen.getByLabelText('Preferred date')
    await userEvent.clear(date)
    await userEvent.type(date, inDays(0))
    await userEvent.click(screen.getByRole('button', { name: 'Send request' }))
    expect(screen.getByText('Choose a date from tomorrow onwards.')).toBeInTheDocument()
    expect(send).not.toHaveBeenCalled()
  })

  it('asks for the consent promise before a photoshoot can be sent', async () => {
    renderWithProviders(<RentalInquiryForm />)
    await fillValid()
    expect(screen.queryByLabelText(PHOTOSHOOT_PROMISE)).not.toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('What is it for?'), 'photoshoot')
    const promise = screen.getByLabelText(PHOTOSHOOT_PROMISE)
    await userEvent.click(screen.getByRole('button', { name: 'Send request' }))
    expect(screen.getByText('Photoshoots need this promise before we can talk dates.')).toBeInTheDocument()
    expect(send).not.toHaveBeenCalled()

    await userEvent.click(promise)
    await userEvent.click(screen.getByRole('button', { name: 'Send request' }))
    await waitFor(() => expect(send).toHaveBeenCalledTimes(1))
    expect(send.mock.calls[0][0]).toMatchObject({
      type: 'photoshoot',
      photoshoot_acknowledged: true,
      duration_hours: 3,
      party_size: 12,
      alternate_date: null,
    })
    const thanks = await screen.findByRole('heading', { name: 'Thank you. Your request is with us.' })
    await waitFor(() => expect(thanks).toHaveFocus())
  })

  it('starts from the signed-in name and email', () => {
    renderWithProviders(<RentalInquiryForm />, { user: verifiedUser })
    expect(screen.getByLabelText('Name or display name')).toHaveValue('night_owl')
    expect(screen.getByLabelText('Email')).toHaveValue('owl@example.org')
  })

  it('keeps the bot trap out of reach', () => {
    renderWithProviders(<RentalInquiryForm />)
    const trap = document.querySelector<HTMLInputElement>('input[name="website"]')!
    expect(trap).toHaveAttribute('tabindex', '-1')
    expect(trap.closest('[aria-hidden="true"]')).not.toBeNull()
  })
})

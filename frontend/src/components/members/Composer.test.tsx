import { fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Edits } from '@/lib/redact'
import { renderWithProviders } from '@/test/render'
import { Composer } from './Composer'

const mocks = vi.hoisted(() => ({
  createPost: vi.fn(),
  exportRedacted: vi.fn(),
  loadSource: vi.fn(),
}))

vi.mock('@/lib/membersApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/membersApi')>()
  return { ...actual, members: { ...actual.members, createPost: mocks.createPost } }
})

vi.mock('@/lib/redact', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/redact')>()
  return {
    ...actual,
    loadSource: mocks.loadSource,
    exportRedacted: mocks.exportRedacted,
    renderRedacted: () => ({ width: 400, height: 300 }),
  }
})

function photo(name: string) {
  return new File([`ORIGINAL BYTES OF ${name}`], name, { type: 'image/jpeg' })
}

beforeEach(() => {
  mocks.createPost.mockReset()
  mocks.exportRedacted.mockReset()
  mocks.loadSource.mockReset()
  mocks.loadSource.mockImplementation(async (file: File) => ({ width: 400, height: 300, name: file.name }))
  mocks.exportRedacted.mockImplementation(async (source: { name: string }, edits: Edits) =>
    new Blob([`redacted ${source.name} with ${edits.redactions.length} cover-ups`], { type: 'image/jpeg' }),
  )
  mocks.createPost.mockResolvedValue({ id: 'abc', state: 'published', in_review: false })
})

function drawRectangle() {
  const surface = screen.getByTestId('redaction-surface')
  surface.getBoundingClientRect = () => ({ left: 0, top: 0, width: 400, height: 300, right: 400, bottom: 300, x: 0, y: 0, toJSON: () => ({}) })
  fireEvent.pointerDown(surface, { clientX: 40, clientY: 30, pointerId: 1 })
  fireEvent.pointerMove(surface, { clientX: 200, clientY: 150, pointerId: 1 })
  fireEvent.pointerUp(surface, { clientX: 200, clientY: 150, pointerId: 1 })
}

async function goToDetails() {
  const onPosted = vi.fn()
  renderWithProviders(<Composer open onClose={() => undefined} onPosted={onPosted} />)
  await userEvent.upload(screen.getByLabelText(/Choose photos/, { selector: 'input' }), [photo('home.jpg'), photo('party.jpg')])
  expect(await screen.findByText(/2 photos chosen/)).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Next' }))

  expect(screen.getByText('Photo 1 of 2')).toBeInTheDocument()
  drawRectangle()
  expect(screen.getByText(/1 area covered/)).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Next' }))

  expect(await screen.findByRole('list', { name: 'Photos in this post' })).toBeInTheDocument()
  await userEvent.type(screen.getByLabelText(/^Describe photo 1/), 'Two candles')
  await userEvent.click(screen.getByRole('button', { name: 'Next' }))
  return onPosted
}

describe('Composer', () => {
  it('walks through the steps and blocks posting until consent is attested', async () => {
    await goToDetails()
    const post = screen.getByRole('button', { name: 'Post' })
    expect(post).toBeDisabled()
    await userEvent.click(post)
    expect(mocks.createPost).not.toHaveBeenCalled()

    await userEvent.click(screen.getByLabelText(/Everyone identifiable in these photos agreed/))
    expect(screen.getByRole('button', { name: 'Post' })).toBeEnabled()
  })

  it('uploads only the redacted renders, never the original files', async () => {
    const onPosted = await goToDetails()
    await userEvent.type(screen.getByLabelText(/^Caption/, { selector: 'textarea' }), 'Quiet night')
    await userEvent.click(screen.getByLabelText(/Everyone identifiable in these photos agreed/))
    await userEvent.click(screen.getByRole('button', { name: 'Post' }))

    await waitFor(() => expect(mocks.createPost).toHaveBeenCalledOnce())
    const draft = mocks.createPost.mock.calls[0][0]
    expect(draft.consentAttested).toBe(true)
    expect(draft.caption).toBe('Quiet night')
    expect(draft.images).toHaveLength(2)
    for (const image of draft.images) {
      expect(image.blob).not.toBeInstanceOf(File)
      expect(await image.blob.text()).not.toContain('ORIGINAL')
    }
    expect(await draft.images[0].blob.text()).toBe('redacted home.jpg with 1 cover-ups')
    expect(await draft.images[1].blob.text()).toBe('redacted party.jpg with 0 cover-ups')
    expect(draft.images[0].alt).toBe('Two candles')
    expect(onPosted).toHaveBeenCalled()
  })

  it('allows a text-only post without attestation', async () => {
    renderWithProviders(<Composer open onClose={() => undefined} onPosted={() => undefined} />)
    await userEvent.click(screen.getByRole('button', { name: 'Write a text post' }))
    expect(screen.queryByLabelText(/Everyone identifiable/)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Post' }))
    expect(await screen.findByText('Write something or add a photo.')).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText(/^Caption/, { selector: 'textarea' }), 'Just words')
    await userEvent.click(screen.getByRole('button', { name: 'Post' }))
    await waitFor(() => expect(mocks.createPost).toHaveBeenCalledOnce())
    expect(mocks.createPost.mock.calls[0][0].images).toEqual([])
  })
})

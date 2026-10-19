import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { renderWithProviders } from '@/test/render'
import { NavDropdown } from './NavDropdown'

const group = {
  label: 'Visit',
  items: [
    { to: '/visit', label: 'Plan Your Visit' },
    { to: '/guests', label: 'Guests' },
    { to: '/faq', label: 'FAQ' },
  ],
}

function renderMenu() {
  renderWithProviders(
    <>
      <NavDropdown group={group} />
      <a href="/after">After</a>
    </>,
  )
  return screen.getByRole('button', { name: 'Visit' })
}

describe('NavDropdown', () => {
  it('is closed until opened and says so', async () => {
    const button = renderMenu()
    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('link', { name: 'Guests' })).not.toBeInTheDocument()
    await userEvent.click(button)
    expect(button).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('link', { name: 'Guests' })).toHaveAttribute('href', '/guests')
  })

  it('opens with Arrow Down and moves through the links with the arrow keys', async () => {
    const button = renderMenu()
    button.focus()
    await userEvent.keyboard('{ArrowDown}')
    await waitFor(() => expect(screen.getByRole('link', { name: 'Plan Your Visit' })).toHaveFocus())
    await userEvent.keyboard('{ArrowDown}')
    expect(screen.getByRole('link', { name: 'Guests' })).toHaveFocus()
    await userEvent.keyboard('{End}')
    expect(screen.getByRole('link', { name: 'FAQ' })).toHaveFocus()
    await userEvent.keyboard('{ArrowDown}')
    expect(screen.getByRole('link', { name: 'Plan Your Visit' })).toHaveFocus()
    await userEvent.keyboard('{ArrowUp}')
    expect(screen.getByRole('link', { name: 'FAQ' })).toHaveFocus()
    await userEvent.keyboard('{Home}')
    expect(screen.getByRole('link', { name: 'Plan Your Visit' })).toHaveFocus()
  })

  it('opens on Enter and closes on Escape, returning focus to the button', async () => {
    const button = renderMenu()
    button.focus()
    await userEvent.keyboard('{Enter}')
    await waitFor(() => expect(screen.getByRole('link', { name: 'Plan Your Visit' })).toHaveFocus())
    await userEvent.keyboard('{Escape}')
    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(button).toHaveFocus()
  })

  it('closes when focus leaves it', async () => {
    const button = renderMenu()
    await userEvent.click(button)
    screen.getByRole('link', { name: 'FAQ' }).focus()
    await userEvent.tab()
    expect(screen.getByRole('link', { name: 'After' })).toHaveFocus()
    expect(button).toHaveAttribute('aria-expanded', 'false')
  })
})

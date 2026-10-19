import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderWithProviders } from '@/test/render'
import { RegisterPage } from './RegisterPage'

describe('RegisterPage', () => {
  it('suggests an email address without a legal name', () => {
    renderWithProviders(<RegisterPage />)
    expect(screen.getByLabelText(/^Email/)).toHaveAccessibleDescription(/Use an email address that doesn't include your legal name\./)
  })
})

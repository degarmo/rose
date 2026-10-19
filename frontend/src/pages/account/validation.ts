export const MIN_PASSWORD_LENGTH = 12
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const DISPLAY_NAME_PATTERN = /^[A-Za-z0-9_.-]{3,30}$/

export function emailError(value: string): string | undefined {
  if (!value.trim()) return 'Enter your email address.'
  if (!EMAIL_PATTERN.test(value.trim())) return 'Enter a full email address, like name@example.com.'
  return undefined
}

export function passwordError(value: string): string | undefined {
  if (!value) return 'Enter a password.'
  if (value.length < MIN_PASSWORD_LENGTH) return `Use at least ${MIN_PASSWORD_LENGTH} characters.`
  return undefined
}

export function displayNameError(value: string): string | undefined {
  if (!value.trim()) return 'Choose a display name.'
  if (!DISPLAY_NAME_PATTERN.test(value.trim())) {
    return 'Use 3 to 30 letters, numbers, dots, dashes or underscores.'
  }
  return undefined
}

export function firstError(errors: Record<string, string | undefined>) {
  return Object.values(errors).find(Boolean)
}

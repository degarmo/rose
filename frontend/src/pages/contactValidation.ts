import type { ContactPayload, ContactTopic, FieldErrors } from '@/lib/api'

export const TOPIC_OPTIONS: { value: ContactTopic; label: string }[] = [
  { value: 'general', label: 'General question' },
  { value: 'membership', label: 'Membership' },
  { value: 'events', label: 'Events and classes' },
  { value: 'volunteer', label: 'Volunteering' },
  { value: 'concern', label: 'Report a concern' },
]

export const EMPTY_FORM: ContactPayload = {
  name: '',
  email: '',
  phone: '',
  topic: 'general',
  message: '',
  website: '',
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PHONE_PATTERN = /^[0-9+().\-\s]{7,32}$/

export type ContactField = 'name' | 'email' | 'phone' | 'topic' | 'message'

export function validateField(field: ContactField, values: ContactPayload): string | undefined {
  const value = values[field].trim()
  switch (field) {
    case 'name':
      if (value.length < 2) return 'Please tell us what to call you.'
      if (value.length > 120) return 'Please keep this under 120 characters.'
      return undefined
    case 'email':
      if (!value) return 'We need an email address to reply.'
      if (!EMAIL_PATTERN.test(value)) return 'Enter a full email address, like name@example.com.'
      return undefined
    case 'phone':
      if (value && !PHONE_PATTERN.test(value)) return 'Enter a valid phone number, or leave it blank.'
      return undefined
    case 'topic':
      if (!TOPIC_OPTIONS.some((option) => option.value === value)) return 'Choose a topic.'
      return undefined
    case 'message':
      if (value.length < 10) return 'Please write a little more so we can help.'
      if (value.length > 5000) return 'Please keep your message under 5,000 characters.'
      return undefined
  }
}

export const FIELDS: ContactField[] = ['name', 'email', 'phone', 'topic', 'message']

export function validateAll(values: ContactPayload): FieldErrors {
  const errors: FieldErrors = {}
  for (const field of FIELDS) {
    const error = validateField(field, values)
    if (error) errors[field] = error
  }
  return errors
}

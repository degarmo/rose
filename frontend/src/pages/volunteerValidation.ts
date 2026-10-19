import type { FieldErrors, VolunteerPayload } from '@/lib/api'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
export const VOLUNTEER_FIELDS = ['contact_name', 'contact_email', 'interests', 'availability', 'experience_note'] as const

export function validateVolunteer(values: VolunteerPayload): FieldErrors {
  const errors: FieldErrors = {}
  if (values.contact_name.trim().length < 2) errors.contact_name = 'Please tell us what to call you.'
  if (!values.contact_email.trim()) errors.contact_email = 'We need an email address to reply.'
  else if (!EMAIL_PATTERN.test(values.contact_email.trim()))
    errors.contact_email = 'That email address does not look quite right.'
  if (values.interests.length === 0) errors.interests = 'Choose at least one way you would like to help.'
  if (values.availability.length === 0) errors.availability = 'Choose when you are usually free.'
  if (values.experience_note.length > 2000) errors.experience_note = 'Please keep this under 2,000 characters.'
  return errors
}


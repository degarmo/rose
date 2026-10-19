import type { FieldErrors, RentalInquiryPayload, RentalType } from '@/lib/api'
import { chicagoDateKey } from '@/lib/format'

export const RENTAL_TYPES: { value: RentalType; label: string }[] = [
  { value: 'private_session', label: 'Private session' },
  { value: 'workshop', label: 'Workshop or class' },
  { value: 'photoshoot', label: 'Photoshoot' },
  { value: 'group_event', label: 'Group event' },
  { value: 'other', label: 'Something else' },
]

export const DURATIONS = Array.from({ length: 12 }, (_, index) => index + 1)

export const PHOTOSHOOT_PROMISE =
  'Everyone photographed will consent, and no other guests or members will appear in any image.'

export const EMPTY_RENTAL: RentalInquiryPayload = {
  contact_name: '',
  contact_email: '',
  contact_phone: '',
  type: '',
  preferred_date: '',
  alternate_date: null,
  start_time: '',
  duration_hours: null,
  party_size: null,
  notes: '',
  photoshoot_acknowledged: false,
  website: '',
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PHONE_PATTERN = /^[0-9+().\-\s]{7,32}$/

export type RentalField =
  | 'contact_name'
  | 'contact_email'
  | 'contact_phone'
  | 'type'
  | 'preferred_date'
  | 'alternate_date'
  | 'start_time'
  | 'duration_hours'
  | 'party_size'
  | 'notes'
  | 'photoshoot_acknowledged'

export const RENTAL_FIELDS: RentalField[] = [
  'contact_name',
  'contact_email',
  'contact_phone',
  'type',
  'preferred_date',
  'alternate_date',
  'start_time',
  'duration_hours',
  'party_size',
  'notes',
  'photoshoot_acknowledged',
]

/** Tomorrow or later, in Chicago time. */
function isFutureDate(value: string, today = chicagoDateKey(new Date())): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && value > today
}

export function validateRentalField(field: RentalField, values: RentalInquiryPayload): string | undefined {
  switch (field) {
    case 'contact_name': {
      const value = values.contact_name.trim()
      if (value.length < 2) return 'Please tell us what to call you.'
      if (value.length > 120) return 'Please keep this under 120 characters.'
      return undefined
    }
    case 'contact_email': {
      const value = values.contact_email.trim()
      if (!value) return 'We need an email address to reply.'
      if (!EMAIL_PATTERN.test(value)) return 'Enter a full email address, like name@example.com.'
      return undefined
    }
    case 'contact_phone': {
      const value = values.contact_phone.trim()
      if (value && !PHONE_PATTERN.test(value)) return 'Enter a valid phone number, or leave it blank.'
      return undefined
    }
    case 'type':
      return RENTAL_TYPES.some((option) => option.value === values.type) ? undefined : 'Choose what the space is for.'
    case 'preferred_date':
      if (!values.preferred_date) return 'Choose a date.'
      return isFutureDate(values.preferred_date) ? undefined : 'Choose a date from tomorrow onwards.'
    case 'alternate_date':
      if (!values.alternate_date) return undefined
      if (!isFutureDate(values.alternate_date)) return 'Choose a date from tomorrow onwards.'
      if (values.alternate_date === values.preferred_date) return 'Choose a different date from your first choice.'
      return undefined
    case 'start_time':
      return /^\d{2}:\d{2}/.test(values.start_time) ? undefined : 'Choose a start time.'
    case 'duration_hours':
      return values.duration_hours && values.duration_hours >= 1 && values.duration_hours <= 12
        ? undefined
        : 'Choose how many hours.'
    case 'party_size':
      return values.party_size && values.party_size >= 1 && values.party_size <= 200
        ? undefined
        : 'Tell us how many people, from 1 to 200.'
    case 'notes':
      return values.notes.length > 3000 ? 'Please keep this under 3,000 characters.' : undefined
    case 'photoshoot_acknowledged':
      return values.type === 'photoshoot' && !values.photoshoot_acknowledged
        ? 'Photoshoots need this promise before we can talk dates.'
        : undefined
  }
}

export function validateRental(values: RentalInquiryPayload): FieldErrors {
  const errors: FieldErrors = {}
  for (const field of RENTAL_FIELDS) {
    const error = validateRentalField(field, values)
    if (error) errors[field] = error
  }
  return errors
}

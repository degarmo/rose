import type { EventCategory, RSVPState, RSVPStateName } from './api'

type Tone = 'neutral' | 'rose' | 'brass'

const STATE_LABELS: Record<RSVPStateName, { label: string; tone: Tone }> = {
  open: { label: 'Open', tone: 'brass' },
  waitlist: { label: 'Waitlist', tone: 'rose' },
  full: { label: 'Full', tone: 'neutral' },
  closed: { label: 'Closed', tone: 'neutral' },
  unavailable: { label: 'Closed', tone: 'neutral' },
  members_only: { label: 'Members only', tone: 'neutral' },
  not_open_yet: { label: 'Opens soon', tone: 'neutral' },
  going: { label: 'Going', tone: 'brass' },
  waitlisted: { label: 'On the waitlist', tone: 'rose' },
}

export function rsvpBadge(rsvp: RSVPState) {
  return STATE_LABELS[rsvp.state]
}

export const EVENT_CATEGORIES: Array<{ value: EventCategory | ''; label: string }> = [
  { value: '', label: 'All events' },
  { value: 'education', label: 'Education nights' },
  { value: 'social', label: 'Socials' },
  { value: 'workshop', label: 'Workshops' },
  { value: 'member_night', label: 'Member nights' },
  { value: 'special', label: 'Special events' },
]

export function isEventCategory(value: string | null): value is EventCategory {
  return EVENT_CATEGORIES.some((option) => option.value === value && value !== '')
}

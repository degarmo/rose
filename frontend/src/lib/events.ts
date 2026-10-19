import type { BadgeTone } from '@/components/ui'
import type { EventCategory, RSVPState, RSVPStateName } from './api'

/** The status badge for each RSVP state (design system: "Status badges"). */
const STATE_LABELS: Record<RSVPStateName, { label: string; tone: BadgeTone }> = {
  open: { label: 'Open', tone: 'open' },
  waitlist: { label: 'Waitlist', tone: 'wait' },
  full: { label: 'Full', tone: 'full' },
  closed: { label: 'Closed', tone: 'full' },
  unavailable: { label: 'Closed', tone: 'full' },
  members_only: { label: 'Members only', tone: 'members' },
  not_open_yet: { label: 'Opens soon', tone: 'full' },
  tier_event_not_included: { label: 'Not on your plan', tone: 'members' },
  monthly_limit_reached: { label: 'Monthly limit reached', tone: 'full' },
  restricted: { label: 'Paused', tone: 'full' },
  going: { label: 'Going', tone: 'going' },
  waitlisted: { label: 'On the waitlist', tone: 'wait' },
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

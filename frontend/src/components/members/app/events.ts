import type { EventSummary } from '@/lib/api'

/** The Chicago clock time of an event: "7:00 PM". */
export const timeOnly = new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit', timeZone: 'America/Chicago' })

/** What the rail offers for an event, by the viewer's own RSVP state. */
export function eventAction(event: EventSummary): { status: string; action: string } {
  switch (event.rsvp.state) {
    case 'going':
      return { status: 'Going', action: 'Going' }
    case 'waitlisted':
      return { status: 'Waitlist', action: 'On the list' }
    case 'waitlist':
      return { status: 'Waitlist', action: 'Join list' }
    case 'open':
      return { status: 'Open', action: 'RSVP' }
    case 'members_only':
      return { status: 'Members only', action: 'Details' }
    default:
      return { status: 'Full', action: 'Details' }
  }
}

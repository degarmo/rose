import { CalendarDays } from 'lucide-react'
import { Link } from 'react-router'
import { timeOnly } from '@/components/members/app/events'
import { DateTile } from '@/components/members/app/RightRail'
import { appButtonClasses } from '@/components/members/app/ui'
import { api } from '@/lib/api'
import { useAsync } from '@/lib/useAsync'
import { EmptyNote, LoadError, Skeleton, StatusChip } from './ui'

/** Your upcoming RSVPs, each with its status: Going or On the waitlist. */
export function UpcomingPlans() {
  const state = useAsync(() => api.myRSVPs(), 'my-rsvps')
  if (state.status === 'loading') return <Skeleton lines={3} />
  if (state.status === 'error') return <LoadError title="Your plans did not load" onRetry={state.retry} />
  if (state.data.length === 0) {
    return (
      <EmptyNote
        icon={CalendarDays}
        title="No plans yet"
        action={
          <Link to="/events" className={appButtonClasses('secondary')}>
            See events
          </Link>
        }
      >
        RSVP to an evening and it shows here with your place.
      </EmptyNote>
    )
  }
  return (
    <ul className="flex flex-col">
      {state.data.map((item) => (
        <li key={item.event.slug} className="relative flex min-h-16 items-center gap-3 border-b border-border py-2 last:border-b-0">
          <DateTile iso={item.event.starts_at} />
          <span className="min-w-0 flex-1">
            <Link to={`/events/${item.event.slug}`} className="block truncate font-semibold text-fg after:absolute after:inset-0">
              {item.event.title}
            </Link>
            <span className="block text-meta text-fg-muted">
              <time dateTime={item.event.starts_at}>{timeOnly.format(new Date(item.event.starts_at))}</time>
              {item.party_size > 1 && ` · Party of ${item.party_size}`}
            </span>
          </span>
          <StatusChip tone={item.status === 'going' ? 'ok' : 'wait'}>{item.status === 'going' ? 'Going' : 'On the waitlist'}</StatusChip>
        </li>
      ))}
    </ul>
  )
}

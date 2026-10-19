import { ArrowRight, BookOpen, Camera, CalendarDays, Check, CircleUser, Heart, Lock, Sparkles } from 'lucide-react'
import { Link } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { PhoneBar } from '@/components/members/app/Nav'
import { Wordmark } from '@/components/members/app/primitives'
import { eventAction, timeOnly } from '@/components/members/app/events'
import { DateTile } from '@/components/members/app/RightRail'
import { appButtonClasses, ICON } from '@/components/members/app/ui'
import { MembershipCard, NoMembership } from '@/components/members/settings/MembershipCard'
import { Card, EmptyNote, LoadError, Skeleton, StatusChip, VerifyEmailBanner } from '@/components/members/settings/ui'
import { api } from '@/lib/api'
import { isOpen, membershipApi, type MyMembership } from '@/lib/membershipApi'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

function greeting(now = new Date()) {
  const hour = Number(
    new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      hourCycle: 'h23',
      timeZone: 'America/Chicago',
    }).format(now),
  )
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

/** The next evenings, each with your RSVP status. */
function ComingUp() {
  const events = useAsync(() => api.events(), 'home-events')
  if (events.status === 'loading') return <Skeleton lines={4} />
  if (events.status === 'error') return <LoadError title="Events did not load" onRetry={events.retry} />
  if (events.data.length === 0) {
    return (
      <EmptyNote
        icon={CalendarDays}
        title="Nothing on the calendar yet"
        action={
          <Link to="/events" className={appButtonClasses('secondary')}>
            See all events
          </Link>
        }
      >
        New evenings are added every week.
      </EmptyNote>
    )
  }
  return (
    <>
      <ul>
        {events.data.slice(0, 5).map((event) => {
          const { status, action } = eventAction(event)
          return (
            <li key={event.id} className="relative flex min-h-16 items-center gap-3 border-b border-border py-2 last:border-b-0">
              <DateTile iso={event.starts_at} />
              <span className="min-w-0 flex-1">
                <Link to={`/events/${event.slug}`} className="block truncate font-semibold text-fg after:absolute after:inset-0">
                  {event.title}
                </Link>
                <span className="block text-meta text-fg-muted">
                  {timeOnly.format(new Date(event.starts_at))}
                  {event.rsvp.state !== 'going' && event.rsvp.state !== 'waitlisted' && ` · ${status}`}
                </span>
              </span>
              {event.rsvp.state === 'going' ? (
                <StatusChip tone="ok">Going</StatusChip>
              ) : event.rsvp.state === 'waitlisted' ? (
                <StatusChip tone="wait">On the waitlist</StatusChip>
              ) : (
                <span className="text-meta font-semibold text-link">{action}</span>
              )}
            </li>
          )
        })}
      </ul>
      <Link to="/events" className="mt-3 inline-flex min-h-11 items-center gap-1 text-sm font-semibold text-link hover:text-primary-hover">
        All events
        <ArrowRight aria-hidden="true" className="size-4" />
      </Link>
    </>
  )
}

/** What the plan includes: its perks, as the plans page lists them. */
function PlanIncludes({ membership }: { membership: MyMembership }) {
  const perks = membership.tier.perks.length ? membership.tier.perks : [membership.tier.description].filter(Boolean)
  if (perks.length === 0) return null
  return (
    <Card title={`${membership.tier.name} includes`}>
      <ul className="flex flex-col gap-2">
        {perks.map((perk) => (
          <li key={perk} className="flex gap-2 text-fg">
            <Check aria-hidden="true" size={18} strokeWidth={ICON.activeStroke} className="mt-0.5 shrink-0 text-link" />
            {perk}
          </li>
        ))}
      </ul>
    </Card>
  )
}

const FEED_ADDS = [
  {
    icon: Camera,
    text: 'A private feed of photos and notes, seen only by members',
  },
  { icon: Sparkles, text: 'Stories from the club and from other members' },
  {
    icon: CircleUser,
    text: 'A profile with a picture that doesn’t have to be you',
  },
  { icon: Heart, text: 'Likes, comments and saved posts' },
]

/** What unlocking the member feed would add, with the next step. */
function FeedUnlock() {
  const auth = useAuth()
  const app = auth.user?.member_app ?? null
  return (
    <Card title="The member community" icon={Lock}>
      <p className="text-fg-muted">
        {app === 'paused' ? 'Your feed access is paused. It reopens when the pause ends.' : 'It stays off until you turn it on. Unlocking it adds:'}
      </p>
      <ul className="mt-3 flex flex-col gap-2.5">
        {FEED_ADDS.map(({ icon: Icon, text }) => (
          <li key={text} className="flex gap-3 text-fg">
            <Icon aria-hidden="true" size={20} strokeWidth={ICON.stroke} className="shrink-0 text-fg-muted" />
            {text}
          </li>
        ))}
      </ul>
      {app !== 'paused' && (
        <Link to={app === 'join' ? '/members/join-feed' : '/membership'} className={appButtonClasses('primary', 'mt-4')}>
          {app === 'join' ? 'Join the member feed' : 'See plans with the feed'}
        </Link>
      )}
    </Card>
  )
}

/**
 * Home for accounts without the feed (design: the member app's shell): a greeting, the
 * membership card or the way to one, the next evenings with your RSVP status, what the plan
 * includes and what the member feed would add.
 */
export function HomePage() {
  useDocumentMeta({ title: 'Home', noindex: true })
  const auth = useAuth()
  const membership = useAsync(() => membershipApi.me(), 'my-membership')
  const user = auth.user
  if (!user) return null
  const current = membership.status === 'success' ? membership.data.membership : null

  return (
    <>
      <PhoneBar
        title={
          <Link to="/members/home" className="flex items-center">
            <Wordmark className="text-2xl" />
            <span className="sr-only">Home</span>
          </Link>
        }
      />
      <div className="mx-auto flex w-full max-w-[935px] flex-col gap-4 px-4 pb-12 pt-3 md:px-8 md:pt-10">
        <header>
          <p className="text-meta text-fg-muted">{greeting()}</p>
          <h1 className="text-2xl font-semibold text-fg">{user.display_name}</h1>
        </header>
        {!user.email_verified && <VerifyEmailBanner />}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-start">
          <div className="flex min-w-0 flex-col gap-4">
            {membership.status === 'loading' && (
              <div className="rounded-app border border-border p-4">
                <Skeleton lines={4} />
              </div>
            )}
            {membership.status === 'error' && <LoadError title="Your membership did not load" onRetry={membership.retry} />}
            {membership.status === 'success' &&
              (current ? (
                <MembershipCard
                  membership={current}
                  footer={
                    <Link to="/members/settings/membership" className={appButtonClasses('secondary', 'self-start')}>
                      Manage membership
                    </Link>
                  }
                />
              ) : (
                <NoMembership />
              ))}
            {current && isOpen(current) && <PlanIncludes membership={current} />}
          </div>
          <div className="flex min-w-0 flex-col gap-4">
            <Card title="Coming up" icon={CalendarDays}>
              <ComingUp />
            </Card>
            {user.feed_access ? (
              <Card title="The member feed" icon={BookOpen}>
                <p className="text-fg-muted">Your feed is open.</p>
                <Link to="/members/feed" className={appButtonClasses('primary', 'mt-3')}>
                  Open the feed
                </Link>
              </Card>
            ) : (
              <FeedUnlock />
            )}
          </div>
        </div>
      </div>
    </>
  )
}

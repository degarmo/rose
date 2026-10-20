import { ArrowRight, CalendarDays, Check } from 'lucide-react'
import { Link } from 'react-router'
import { Logo } from '@/components/brand/Logo'
import { useAuth } from '@/components/layout/authContext'
import { PhoneBar } from '@/components/members/app/Nav'
import { eventAction, timeOnly } from '@/components/members/app/events'
import { DateTile } from '@/components/members/app/RightRail'
import { appButtonClasses, ICON } from '@/components/members/app/ui'
import { CommunityTeaser } from '@/components/members/home/CommunityTeaser'
import { WhatsMissing } from '@/components/members/home/WhatsMissing'
import { MembershipCard, NoMembership } from '@/components/members/settings/MembershipCard'
import { Card, EmptyNote, LoadError, Skeleton, StatusChip, VerifyEmailBanner } from '@/components/members/settings/ui'
import { api, ApiError } from '@/lib/api'
import { isOpen, membershipApi, type MyMembership } from '@/lib/membershipApi'
import { feedAccount } from '@/lib/membersApi'
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
  const events = useAsync(() => api.events('', 1, 5), 'home-events')
  if (events.status === 'loading') return <Skeleton lines={4} />
  if (events.status === 'error') return <LoadError title="Events did not load" onRetry={events.retry} />
  if (events.data.count === 0) {
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
        {events.data.results.map((event) => {
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

/**
 * Home (design: the member app's shell): a greeting; "What's missing" between this account
 * and the member community, step by step; the membership card or the way to one; the next
 * evenings with your RSVP status; what the plan includes; and, for accounts without the
 * feed, a preview of it built only from the club's own posts.
 */
export function HomePage() {
  useDocumentMeta({ title: 'Home', noindex: true })
  const auth = useAuth()
  const user = auth.user
  const membership = useAsync(() => membershipApi.me(), 'my-membership')
  const path = useAsync(
    () => feedAccount.path(),
    `feed-path:${user?.email_verified}:${user?.member_app}:${user?.feed_access}`,
  )
  if (!user) return null
  const current = membership.status === 'success' ? membership.data.membership : null
  // With the member feed switched off for the whole site, there is no way in to show.
  const feedOff = path.status === 'error' && path.error instanceof ApiError && path.error.status === 404
  const steps = path.status === 'success' ? path.data.steps : []
  const door = steps.find((step) => step.key === 'door')
  // The door code shows once: in the checklist while the door is still to come.
  const codeInPath = Boolean(door?.key === 'door' && door.reference_code && door.waiting_for !== 'suspended')
  const planChosen = steps.some((step) => step.key === 'plan' && step.state === 'done')
  const cardShowsCode = path.status === 'success' ? !codeInPath : path.status === 'error'

  return (
    <>
      <PhoneBar
        title={
          <Link to="/members/home" className="flex items-center">
            <Logo variant="mark" height={28} decorative priority />
            <span className="sr-only">Home</span>
          </Link>
        }
      />
      <div className="mx-auto flex w-full max-w-[935px] flex-col gap-4 px-4 pb-12 pt-3 md:px-8 md:pt-10">
        <header>
          <p className="text-meta text-fg-muted">{greeting()}</p>
          <h1 className="text-2xl font-semibold text-fg">{user.display_name}</h1>
        </header>
        {!user.email_verified && path.status === 'error' && <VerifyEmailBanner />}
        {path.status === 'loading' && (
          <div className="rounded-app border border-border p-4">
            <Skeleton lines={5} />
          </div>
        )}
        {path.status === 'success' && <WhatsMissing path={path.data} displayName={user.display_name} cardShowsCode={cardShowsCode && isOpen(current)} />}
        {path.status === 'error' && !feedOff && <LoadError title="Your next steps did not load" onRetry={path.retry} />}
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
                  showCode={cardShowsCode}
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
          </div>
        </div>
        {!user.feed_access && !feedOff && <CommunityTeaser showPlans={!planChosen} />}
      </div>
    </>
  )
}

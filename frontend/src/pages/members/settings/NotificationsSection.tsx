import { BellRing, CalendarClock, Heart, IdCard, Lock, MessageCircle } from 'lucide-react'
import { useOptionalMembers } from '@/components/members/membersContext'
import { Card, FeedOnlyNote, LoadError, Skeleton, SwitchRow } from '@/components/members/settings/ui'
import { usePreferences } from '@/components/members/settings/usePreferences'

/** Settings · Notifications: email and in-app switches. Discreet subject lines can't be turned off. */
export function NotificationsSection() {
  const members = useOptionalMembers()
  const { state, preferences, save, saving } = usePreferences()
  if (state.status === 'error' && !preferences) return <LoadError title="Your notification settings did not load" onRetry={state.retry} />

  return (
    <div className="flex flex-col gap-4">
      <Card title="Email">
        {preferences ? (
          <ul>
            <SwitchRow
              icon={CalendarClock}
              label="Event reminders"
              sub="An email before an evening you RSVP'd to"
              checked={preferences.email_event_reminders}
              disabled={saving}
              onChange={(value) => void save({ email_event_reminders: value })}
            />
            <SwitchRow
              icon={IdCard}
              label="Membership reminders"
              sub="Before your membership renews or ends"
              checked={preferences.email_membership_reminders}
              disabled={saving}
              onChange={(value) => void save({ email_membership_reminders: value })}
            />
            <SwitchRow
              icon={Lock}
              label="Discreet subject lines"
              sub="Always on: subjects and the sender never say what an email is about"
              checked
              locked
              onChange={() => undefined}
            />
          </ul>
        ) : (
          <Skeleton lines={3} />
        )}
        <p className="mt-3 text-meta text-fg-muted">Emails about your account itself, like sign-in links, receipts and notices from our team, always arrive.</p>
      </Card>
      <Card title="In the app">
        {!members ? (
          <FeedOnlyNote icon={BellRing} title="In-app notifications">
            Likes and comments on your posts are notifications in the member feed.
          </FeedOnlyNote>
        ) : preferences ? (
          <ul>
            <SwitchRow
              icon={Heart}
              label="Likes"
              sub="When someone likes your post (never who)"
              checked={preferences.notify_likes}
              disabled={saving}
              onChange={(value) => void save({ notify_likes: value })}
            />
            <SwitchRow
              icon={MessageCircle}
              label="Comments"
              sub="When someone comments on your post"
              checked={preferences.notify_comments}
              disabled={saving}
              onChange={(value) => void save({ notify_comments: value })}
            />
          </ul>
        ) : (
          <Skeleton lines={2} />
        )}
        {members && <p className="mt-3 text-meta text-fg-muted">Notices from our team about your posts always show.</p>}
      </Card>
    </div>
  )
}

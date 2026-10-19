import { Heart, MessageCircle, ScrollText, ShieldAlert } from 'lucide-react'
import { useEffect } from 'react'
import { Link } from 'react-router'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { cn } from '@/lib/cn'
import { relativeDate } from '@/lib/format'
import { members, postedLabel, type FeedNotification } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'
import { useMembers } from '../membersContext'

const ICONS = { like: Heart, comment: MessageCircle, moderation: ShieldAlert, guidelines: ScrollText }

function Row({ note, onNavigate }: { note: FeedNotification; onNavigate?: () => void }) {
  const Icon = ICONS[note.kind]
  const content = (
    <>
      <span aria-hidden="true" className="inline-flex size-11 shrink-0 items-center justify-center rounded-full bg-hover">
        <Icon className={cn('size-5', note.kind === 'like' ? 'fill-primary text-primary' : 'text-fg')} />
      </span>
      <span className="flex-1">
        <span className="text-fg">{note.text}</span> <span className="text-fg-muted">{postedLabel(note.posted, relativeDate)}</span>
      </span>
      {!note.read && <span className="size-2 shrink-0 rounded-full bg-primary" aria-label="Unread" />}
    </>
  )
  return note.post_id ? (
    <Link to={`/members/p/${note.post_id}`} onClick={onNavigate} className="flex items-center gap-3 px-6 py-2 hover:bg-surface">
      {content}
    </Link>
  ) : (
    <div className="flex items-center gap-3 px-6 py-2">{content}</div>
  )
}

/** In-app only, never by email. Grouped into this week and earlier; likes stay grouped and nameless. */
export function NotificationsContent({ onNavigate }: { onNavigate?: () => void }) {
  const { refreshMe } = useMembers()
  const state = useAsync(() => members.notifications(), 'notifications')

  useEffect(() => {
    if (state.status !== 'success') return
    if (state.data.results.some((note) => !note.read)) void members.markNotificationsRead().then(refreshMe)
  }, [state.status, state.data, refreshMe])

  if (state.status === 'loading') return <LoadingState label="Loading" />
  if (state.status === 'error') return <ErrorState title="Notifications did not load" onRetry={state.retry} />
  const notes = state.data.results
  if (notes.length === 0) {
    return (
      <div className="px-6">
        <EmptyState title="All quiet" message="Likes, comments and updates from our team show up here." />
      </div>
    )
  }
  const groups = [
    { title: 'This week', notes: notes.filter((note) => note.posted.recent) },
    { title: 'Earlier', notes: notes.filter((note) => !note.posted.recent) },
  ].filter((group) => group.notes.length > 0)

  return (
    <div className="flex flex-col gap-2">
      {groups.map((group) => (
        <section key={group.title} aria-label={group.title} className="border-b border-border pb-3 last:border-b-0">
          <h3 className="px-6 pb-2 pt-3 text-base font-semibold text-fg">{group.title}</h3>
          <ul>
            {group.notes.map((note) => (
              <li key={note.id}>
                <Row note={note} onNavigate={onNavigate} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}

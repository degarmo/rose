import { Heart, MessageCircle, ScrollText, ShieldAlert } from 'lucide-react'
import { useEffect } from 'react'
import { Link } from 'react-router'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { cn } from '@/lib/cn'
import { relativeDate } from '@/lib/format'
import { members, postedLabel, type FeedNotification } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'
import { Avatar } from '../Avatar'
import { useMembers } from '../membersContext'

const ICONS = { like: Heart, comment: MessageCircle, moderation: ShieldAlert, notice: ShieldAlert, guidelines: ScrollText }

/** Where a notification opens: its post, or Settings > Notices for decisions about the account. */
function targetOf(note: FeedNotification) {
  if (note.post_id) return `/members/p/${note.post_id}`
  if (note.kind === 'notice') return '/members/settings/notices'
  return null
}

function Row({ note, onNavigate }: { note: FeedNotification; onNavigate?: () => void }) {
  const Icon = ICONS[note.kind]
  const content = (
    <>
      {note.actor ? (
        <span aria-hidden="true">
          <Avatar member={note.actor} size="md" />
        </span>
      ) : (
        <span aria-hidden="true" className={cn('inline-flex size-11 shrink-0 items-center justify-center rounded-full', note.kind === 'like' ? 'bg-tint' : 'bg-control')}>
          <Icon strokeWidth={1.8} className={cn('size-5', note.kind === 'like' ? 'fill-primary text-primary' : 'text-fg')} />
        </span>
      )}
      <span className="flex-1 leading-[18px]">
        <span className="text-fg">{note.text}</span> <span className="text-fg-muted">{postedLabel(note.posted, relativeDate)}</span>
      </span>
      {!note.read && <span className="size-2 shrink-0 rounded-full bg-primary" aria-label="Unread" />}
      {note.thumbnail && (
        <span aria-hidden="true" className="wash-rose size-11 shrink-0 overflow-hidden rounded-[4px]">
          <img src={note.thumbnail} alt="" draggable={false} loading="lazy" className="size-full select-none object-cover" />
        </span>
      )}
    </>
  )
  const target = targetOf(note)
  return target ? (
    <Link to={target} onClick={onNavigate} className="flex items-center gap-3 px-4 py-2 hover:bg-surface md:px-6">
      {content}
    </Link>
  ) : (
    <div className="flex items-center gap-3 px-4 py-2 md:px-6">{content}</div>
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
      <div className="px-4 md:px-6">
        <EmptyState title="All quiet" message="Likes, comments and updates from our team show up here." />
      </div>
    )
  }
  const groups = [
    { title: 'This week', notes: notes.filter((note) => note.posted.recent) },
    { title: 'Earlier', notes: notes.filter((note) => !note.posted.recent) },
  ].filter((group) => group.notes.length > 0)

  return (
    <div className="flex flex-col">
      {groups.map((group, index) => (
        <section key={group.title} aria-label={group.title} className={cn(index > 0 && 'mt-2 border-t border-border')}>
          <h3 className={cn('px-4 pb-1 text-sm font-semibold text-fg md:px-6', index > 0 ? 'pt-4' : 'pt-3 md:pt-2')}>{group.title}</h3>
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

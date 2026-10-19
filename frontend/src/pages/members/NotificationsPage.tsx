import { Heart, MessageCircle, ScrollText, ShieldAlert } from 'lucide-react'
import { useEffect } from 'react'
import { Link } from 'react-router'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { useMembers } from '@/components/members/membersContext'
import { cn } from '@/lib/cn'
import { relativeDate } from '@/lib/format'
import { members, postedLabel } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

const ICONS = { like: Heart, comment: MessageCircle, moderation: ShieldAlert, guidelines: ScrollText }

export function NotificationsPage() {
  useDocumentMeta({ title: 'Notifications', noindex: true })
  const { refreshMe } = useMembers()
  const state = useAsync(() => members.notifications(), 'notifications')

  useEffect(() => {
    if (state.status !== 'success') return
    if (state.data.results.some((n) => !n.read)) {
      void members.markNotificationsRead().then(refreshMe)
    }
  }, [state.status, state.data, refreshMe])

  return (
    <div>
      <h1 className="text-2xl text-fg">Notifications</h1>
      <p className="mt-1 text-sm text-fg-subtle">Only here, never by email.</p>
      <div className="mt-6">
        {state.status === 'loading' && <LoadingState label="Loading" />}
        {state.status === 'error' && <ErrorState title="Notifications did not load" onRetry={state.retry} />}
        {state.status === 'success' && state.data.results.length === 0 && <EmptyState title="All quiet" message="Likes, comments and updates from our team show up here." />}
        {state.status === 'success' && state.data.results.length > 0 && (
          <ul className="flex flex-col">
            {state.data.results.map((note) => {
              const Icon = ICONS[note.kind]
              const content = (
                <>
                  <span aria-hidden="true" className="inline-flex size-11 shrink-0 items-center justify-center rounded-full bg-primary-deep">
                    <Icon className={cn('size-5', note.kind === 'like' ? 'fill-rose text-rose' : 'text-fg')} />
                  </span>
                  <span className="flex-1 text-sm">
                    <span className={cn(note.read ? 'text-fg-muted' : 'text-fg')}>{note.text}</span>{' '}
                    <span className="text-fg-subtle">{postedLabel(note.posted, relativeDate)}</span>
                  </span>
                  {!note.read && <span className="size-2 shrink-0 rounded-full bg-primary" aria-label="Unread" />}
                </>
              )
              return (
                <li key={note.id}>
                  {note.post_id ? (
                    <Link to={`/members/p/${note.post_id}`} className="-mx-2 flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-primary-deep">
                      {content}
                    </Link>
                  ) : (
                    <div className="flex items-center gap-3 py-2">{content}</div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}

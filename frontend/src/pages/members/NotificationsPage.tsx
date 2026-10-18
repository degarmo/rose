import { Bell, Heart, MessageCircle, ScrollText, ShieldAlert } from 'lucide-react'
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
      <h1 className="flex items-center gap-2 text-3xl text-fg">
        <Bell aria-hidden="true" className="size-6 text-highlight" />
        Notifications
      </h1>
      <p className="mt-2 text-sm text-fg-subtle">Only here, never by email.</p>
      <div className="mt-6">
        {state.status === 'loading' && <LoadingState label="Loading" />}
        {state.status === 'error' && <ErrorState title="Notifications did not load" onRetry={state.retry} />}
        {state.status === 'success' && state.data.results.length === 0 && <EmptyState title="All quiet" message="Likes, comments and updates from our team show up here." />}
        {state.status === 'success' && state.data.results.length > 0 && (
          <ul className="flex flex-col divide-y divide-border">
            {state.data.results.map((note) => {
              const Icon = ICONS[note.kind]
              const content = (
                <>
                  <Icon aria-hidden="true" className={cn('mt-0.5 size-5 shrink-0', note.kind === 'like' ? 'text-rose' : 'text-highlight')} />
                  <span className="flex-1">
                    <span className={cn('block', note.read ? 'text-fg-muted' : 'text-fg')}>{note.text}</span>
                    <span className="text-xs text-fg-subtle">{postedLabel(note.posted, relativeDate)}</span>
                  </span>
                  {!note.read && <span className="mt-2 size-2 rounded-full bg-rose" aria-label="Unread" />}
                </>
              )
              return (
                <li key={note.id}>
                  {note.post_id ? (
                    <Link to={`/members/p/${note.post_id}`} className="flex gap-3 py-4 hover:bg-surface">
                      {content}
                    </Link>
                  ) : (
                    <div className="flex gap-3 py-4">{content}</div>
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

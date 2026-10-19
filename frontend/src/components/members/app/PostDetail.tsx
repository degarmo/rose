import { useId, useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { relativeDate } from '@/lib/format'
import { members, postedLabel, type FeedComment, type FeedPost } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'
import { useToast } from '../../ui'
import { Avatar } from '../Avatar'
import { ConfirmDialog } from '../ConfirmDialog'
import { ReportDialog } from '../ReportDialog'
import { SensitiveBlur } from '../SensitiveBlur'
import { useMembers } from '../membersContext'
import { ActionSheet } from './ActionSheet'
import { ActionRow, Caption, CommentForm, LikesLine, PostHeader } from './PostCard'
import { profilePath } from './postUtils'
import { useLatestPost, usePostActions } from './usePost'
import { MediaCarousel } from './MediaCarousel'

function CommentRow({ comment, onOptions }: { comment: FeedComment; onOptions: () => void }) {
  return (
    <li className="group flex gap-3 py-2">
      {/* A second way to the same profile as the name; hidden from the tab order and screen readers. */}
      <Link to={profilePath(comment.author.handle)} className="shrink-0" tabIndex={-1} aria-hidden="true">
        <Avatar member={comment.author} size="sm" />
      </Link>
      <div className="min-w-0 flex-1">
        <p className="break-words text-fg">
          <Link to={profilePath(comment.author.handle)} className="font-semibold">
            {comment.author.handle}
          </Link>{' '}
          <span
            className="[&_a]:text-accent [&_a]:underline"
            // Sanitised on the server.
            dangerouslySetInnerHTML={{ __html: comment.body_html }}
          />
        </p>
        <p className="mt-1 flex items-center gap-3 text-xs text-fg-muted">
          {postedLabel(comment.posted, relativeDate)}
          <button type="button" onClick={onOptions} className="font-semibold text-fg-muted hover:text-fg">
            Options<span className="sr-only"> for {comment.author.handle}'s comment</span>
          </button>
        </p>
      </div>
    </li>
  )
}

function Comments({ post, version, onDeleted }: { post: FeedPost; version: number; onDeleted: () => void }) {
  const toast = useToast()
  const state = useAsync(() => members.comments(post.id), `${post.id}|${version}`)
  const [chosen, setChosen] = useState<FeedComment | null>(null)
  const [dialog, setDialog] = useState<'sheet' | 'report' | 'delete' | null>(null)

  if (state.status === 'loading') return <LoadingState label="Loading comments" />
  if (state.status === 'error') return <ErrorState title="Comments did not load" onRetry={state.retry} />

  async function remove(comment: FeedComment) {
    try {
      await members.deleteComment(comment.id)
      setDialog(null)
      onDeleted()
      toast.show({ tone: 'success', title: 'Comment deleted' })
    } catch {
      toast.show({ tone: 'error', title: 'That did not work' })
    }
  }

  return (
    <>
      <h2 className="sr-only">Comments</h2>
      {state.data.length === 0 && <p className="py-2 text-fg-muted">{post.comments_enabled ? 'No comments yet.' : 'Comments are off for this post.'}</p>}
      <ul>
        {state.data.map((comment) => (
          <CommentRow
            key={comment.id}
            comment={comment}
            onOptions={() => {
              setChosen(comment)
              setDialog('sheet')
            }}
          />
        ))}
      </ul>
      <ActionSheet
        open={dialog === 'sheet'}
        onClose={() => setDialog((d) => (d === 'sheet' ? null : d))}
        label="Comment options"
        actions={[
          ...(chosen?.can_delete ? [{ label: 'Delete', onSelect: () => setDialog('delete'), danger: true }] : []),
          { label: 'Report', onSelect: () => setDialog('report'), danger: !chosen?.can_delete },
        ]}
      />
      <ReportDialog open={dialog === 'report'} onClose={() => setDialog(null)} targetType="comment" targetId={chosen?.id ?? ''} />
      <ConfirmDialog
        open={dialog === 'delete'}
        title="Delete this comment?"
        confirmLabel="Delete"
        onClose={() => setDialog(null)}
        onConfirm={() => chosen && void remove(chosen)}
      >
        <p>This cannot be undone.</p>
      </ConfirmDialog>
    </>
  )
}

/** Everything about one post. `modal`: media left, 335px panel right. `page`: one column for phones. */
function Detail({ post, layout }: { post: FeedPost; layout: 'modal' | 'page' }) {
  const latest = useLatestPost(post)
  if (!latest) return <p className="p-8 text-fg-muted">This post was deleted.</p>
  return <LiveDetail post={latest} layout={layout} />
}

function LiveDetail({ post: latest, layout }: { post: FeedPost; layout: 'modal' | 'page' }) {
  const { patchPost } = useMembers()
  const { toggleLike, likeOnce, toggleSave, openSheet, dialogs } = usePostActions(latest)
  const [version, setVersion] = useState(0)
  const inputId = useId()
  const canComment = latest.comments_enabled && (latest.state === null || latest.state === 'published')

  const media =
    latest.images.length > 0 ? (
      <SensitiveBlur blurred={latest.blur}>
        <MediaCarousel
          images={latest.images}
          label={`Images in ${latest.author.handle}'s post`}
          protect
          onDoubleTap={likeOnce}
          fill={layout === 'modal'}
        />
      </SensitiveBlur>
    ) : null

  const footer = (
    <div className={cn(layout === 'modal' && 'border-t border-border px-4')}>
      <ActionRow
        post={latest}
        onLike={() => void toggleLike()}
        onSave={() => void toggleSave()}
        onComment={canComment ? () => document.getElementById(inputId)?.focus() : undefined}
      />
      <LikesLine post={latest} />
      <time dateTime={latest.posted.at ?? undefined} className="mb-2 mt-1 block text-xs text-fg-muted">
        {postedLabel(latest.posted, relativeDate)}
      </time>
    </div>
  )

  const commentBox = canComment ? (
    <CommentForm
      post={latest}
      inputId={inputId}
      className={cn('border-t border-border', layout === 'modal' ? 'px-4 py-1' : 'py-1')}
      onCommented={(comment) => {
        patchPost(latest, (current) => ({ ...current, comment_count: current.comment_count + 1, recent_comments: [...current.recent_comments, comment].slice(-2) }))
        setVersion((n) => n + 1)
      }}
    />
  ) : null

  const thread = (
    <>
      {latest.caption_html && (
        <div className="flex gap-3 py-2">
          <Avatar member={latest.author} size="sm" />
          <div className="min-w-0 flex-1">
            <Caption post={latest} clamp={false} />
          </div>
        </div>
      )}
      <Comments
        post={latest}
        version={version}
        onDeleted={() => {
          patchPost(latest, (current) => ({ ...current, comment_count: Math.max(current.comment_count - 1, 0) }))
          setVersion((n) => n + 1)
        }}
      />
    </>
  )

  if (layout === 'modal') {
    return (
      <article aria-label={`Post by ${latest.author.handle}`} className="flex h-full max-h-[min(90dvh,900px)] overflow-hidden rounded-r-[4px] bg-canvas">
        <h1 className="sr-only">Post by {latest.author.handle}</h1>
        <div className="flex min-w-0 flex-1 items-center justify-center bg-black">
          {media ?? (
            <div className="flex size-full items-center justify-center bg-surface p-10 text-lg text-fg">
              <p className="line-clamp-[12] max-w-md break-words" dangerouslySetInnerHTML={{ __html: latest.caption_html }} />
            </div>
          )}
        </div>
        <div className="flex w-[335px] shrink-0 flex-col border-l border-border">
          <div className="border-b border-border px-4">
            <PostHeader post={latest} onMore={openSheet} />
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-2">{thread}</div>
          {footer}
          {commentBox}
        </div>
        {dialogs}
      </article>
    )
  }

  return (
    <article aria-label={`Post by ${latest.author.handle}`}>
      <h1 className="sr-only">Post by {latest.author.handle}</h1>
      <PostHeader post={latest} onMore={openSheet} />
      {media && <div className="-mx-3 sm:mx-0 sm:overflow-hidden sm:rounded-[4px] sm:border sm:border-border">{media}</div>}
      {footer}
      {commentBox}
      <div className="border-t border-border pt-2">{thread}</div>
      {dialogs}
    </article>
  )
}

/** Loads one post and shows it in the given layout; `notFound` stands in for a missing post. */
export function PostDetail({ id, layout, notFound }: { id: string; layout: 'modal' | 'page'; notFound: ReactNode }) {
  const state = useAsync(() => members.post(id), id)
  if (state.status === 'loading') return <LoadingState label="Loading post" />
  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) return notFound
  if (state.status === 'error') return <ErrorState title="This post did not load" onRetry={state.retry} />
  return <Detail post={state.data} layout={layout} />
}

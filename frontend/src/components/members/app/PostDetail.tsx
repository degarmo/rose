import { Ellipsis } from 'lucide-react'
import { useId, useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { relativeDate } from '@/lib/format'
import { members, postedLabel, postedShort, type FeedComment, type FeedPost, type Posted } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'
import { useToast } from '../../ui'
import { Avatar } from '../Avatar'
import { ConfirmDialog } from '../ConfirmDialog'
import { ReportDialog } from '../ReportDialog'
import { SensitiveBlur } from '../SensitiveBlur'
import { useMembers } from '../membersContext'
import { ActionSheet } from './ActionSheet'
import { ActionRow, Caption, CommentForm, LikesLine, PostHeader } from './PostCard'
import { mediaRatio, profilePath } from './postUtils'
import { ICON } from './ui'
import { useLatestPost, usePostActions } from './usePost'
import { MediaCarousel } from './MediaCarousel'

/** Design: a 32px avatar, the handle (600) and the words, then "3d · Options" at 12px. */
function CommentRow({ comment, onOptions }: { comment: FeedComment; onOptions: () => void }) {
  return (
    <li className="flex gap-3">
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
            className="[&_a]:text-link [&_a]:underline"
            // Sanitised on the server.
            dangerouslySetInnerHTML={{ __html: comment.body_html }}
          />
        </p>
        <p className="mt-1 flex items-center gap-1 text-meta text-fg-muted">
          <When posted={comment.posted} />
          <span aria-hidden="true">·</span>
          <button type="button" onClick={onOptions} className="min-h-6 font-semibold text-fg-muted hover:text-fg">
            Options<span className="sr-only"> for {comment.author.handle}'s comment</span>
          </button>
        </p>
      </div>
    </li>
  )
}

/** A short time ("3d"), with the exact moment for machines while it is recent. */
function When({ posted }: { posted: Posted }) {
  const label = postedShort(posted)
  return posted.at ? <time dateTime={posted.at}>{label}</time> : <span>{label}</span>
}

function Comments({ post, version, onDeleted }: { post: FeedPost; version: number; onDeleted: () => void }) {
  const toast = useToast()
  const state = useAsync(() => members.comments(post.id), `${post.id}|${version}`)
  const [chosen, setChosen] = useState<FeedComment | null>(null)
  const [dialog, setDialog] = useState<'sheet' | 'report' | 'delete' | null>(null)

  if (state.status === 'loading') return <LoadingState label="Loading comments" className="py-4" />
  if (state.status === 'error') return <ErrorState title="Comments did not load" onRetry={state.retry} className="p-4" />

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
      {state.data.length === 0 && <p className="text-fg-muted">{post.comments_enabled ? 'No comments yet.' : 'Comments are off for this post.'}</p>}
      <ul className="flex flex-col gap-4">
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
          { label: 'Report to hosts', onSelect: () => setDialog('report'), danger: !chosen?.can_delete },
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

/** Everything about one post. `modal`: the picture beside a 335px column. `page`: the post card for phones. */
function Detail({ post, layout }: { post: FeedPost; layout: 'modal' | 'page' }) {
  const latest = useLatestPost(post)
  if (!latest) return <p className={cn('p-8 text-fg-muted', layout === 'modal' && 'rounded-[4px] bg-canvas')}>This post was deleted.</p>
  return <LiveDetail post={latest} layout={layout} />
}

/** The timestamp under the actions (design: 10px caps). */
function Stamp({ posted, className }: { posted: Posted; className?: string }) {
  const label = postedLabel(posted, relativeDate)
  const style = cn('block text-[0.625rem] uppercase leading-[18px] tracking-[0.2px] text-fg-muted', className)
  return posted.at ? (
    <time dateTime={posted.at} className={style}>
      {label}
    </time>
  ) : (
    <span className={style}>{label}</span>
  )
}

/**
 * The picture's height in the modal (design: 760px, the width following the post's
 * shape), shrunk to fit shorter or narrower windows beside the 335px column.
 */
function modalMediaSize(ratio: number) {
  const height = `min(760px, calc(100dvh - 80px), calc((100vw - 96px - 335px) / ${ratio.toFixed(4)}))`
  return { height, width: `calc(${height} * ${ratio.toFixed(4)})` }
}

function LiveDetail({ post: latest, layout }: { post: FeedPost; layout: 'modal' | 'page' }) {
  const { patchPost } = useMembers()
  const { toggleLike, likeOnce, toggleSave, openSheet, dialogs } = usePostActions(latest)
  const [version, setVersion] = useState(0)
  const inputId = useId()
  const canComment = latest.comments_enabled && (latest.state === null || latest.state === 'published')
  const modal = layout === 'modal'

  const media =
    latest.images.length > 0 ? (
      <SensitiveBlur blurred={latest.blur}>
        <MediaCarousel
          images={latest.images}
          label={`Images in ${latest.author.handle}'s post`}
          protect
          onDoubleTap={likeOnce}
          fill={modal}
          dotsBelow={!modal}
        />
      </SensitiveBlur>
    ) : null

  const actions = (
    <ActionRow
      post={latest}
      onLike={() => void toggleLike()}
      onSave={() => void toggleSave()}
      onComment={canComment ? () => document.getElementById(inputId)?.focus() : undefined}
    />
  )

  const commentBox = canComment ? (
    <CommentForm
      post={latest}
      inputId={inputId}
      className={modal ? 'border-t border-border px-4 py-2.5' : 'pt-1.5'}
      onCommented={(comment) => {
        patchPost(latest, (current) => ({ ...current, comment_count: current.comment_count + 1, recent_comments: [...current.recent_comments, comment].slice(-2) }))
        setVersion((n) => n + 1)
      }}
    />
  ) : null

  const comments = (
    <Comments
      post={latest}
      version={version}
      onDeleted={() => {
        patchPost(latest, (current) => ({ ...current, comment_count: Math.max(current.comment_count - 1, 0) }))
        setVersion((n) => n + 1)
      }}
    />
  )

  if (modal) {
    return (
      <article aria-label={`Post by ${latest.author.handle}`} className="flex max-w-full overflow-hidden rounded-[4px] bg-canvas shadow-modal">
        <h1 className="sr-only">Post by {latest.author.handle}</h1>
        <div className="relative shrink-0 bg-black" style={modalMediaSize(media ? mediaRatio(latest.images) : 4 / 5)}>
          {media ?? (
            <div className="flex size-full items-center justify-center bg-surface p-10 text-lg text-fg">
              <p className="line-clamp-[12] max-w-md break-words" dangerouslySetInnerHTML={{ __html: latest.caption_html }} />
            </div>
          )}
        </div>
        <div className="flex w-[335px] shrink-0 flex-col border-l border-border">
          <header className="flex h-[60px] shrink-0 items-center gap-3 border-b border-border px-4">
            <Link to={profilePath(latest.author.handle)} className="flex min-w-0 flex-1 items-center gap-3">
              <Avatar member={latest.author} size="sm" />
              <span className="truncate font-semibold text-fg">{latest.author.handle}</span>
            </Link>
            <button type="button" onClick={openSheet} className="-mr-2 inline-flex size-10 items-center justify-center text-fg hover:text-fg-muted">
              <Ellipsis aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} />
              <span className="sr-only">Post options</span>
            </button>
          </header>
          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4">
            {latest.caption_html && (
              <div className="flex gap-3">
                <Avatar member={latest.author} size="sm" />
                <div className="min-w-0 flex-1">
                  <Caption post={latest} clamp={false} />
                  <p className="mt-1 text-meta text-fg-muted">
                    <When posted={latest.posted} />
                  </p>
                </div>
              </div>
            )}
            {comments}
          </div>
          <div className="flex shrink-0 flex-col gap-1.5 border-t border-border px-4 pb-3 pt-1">
            {actions}
            <LikesLine post={latest} />
            <Stamp posted={latest.posted} />
          </div>
          {commentBox}
        </div>
        {dialogs}
      </article>
    )
  }

  return (
    <article aria-label={`Post by ${latest.author.handle}`}>
      <h1 className="sr-only">Post by {latest.author.handle}</h1>
      <div className="border-b border-border pb-3">
        <PostHeader post={latest} onMore={openSheet} />
        {media}
        <div className="px-4 pt-1.5">{actions}</div>
        <div className="flex flex-col gap-1 px-4">
          <LikesLine post={latest} />
          <Caption post={latest} clamp={false} />
          <Stamp posted={latest.posted} className="pt-0.5" />
          {commentBox}
        </div>
      </div>
      <div className="flex flex-col gap-4 px-4 py-4">{comments}</div>
      {dialogs}
    </article>
  )
}

/** Loads one post and shows it in the given layout; `notFound` stands in for a missing post. */
export function PostDetail({ id, layout, notFound }: { id: string; layout: 'modal' | 'page'; notFound: ReactNode }) {
  const state = useAsync(() => members.post(id), id)
  const box = layout === 'modal' ? 'rounded-[4px] bg-canvas px-8' : 'px-4'
  if (state.status === 'loading') return <LoadingState label="Loading post" className={box} />
  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) return notFound
  if (state.status === 'error') return <ErrorState title="This post did not load" onRetry={state.retry} className={layout === 'modal' ? undefined : 'm-4'} />
  return <Detail post={state.data} layout={layout} />
}

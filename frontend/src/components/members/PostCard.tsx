import { Heart, Hourglass, MessageCircle } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { cn } from '@/lib/cn'
import { relativeDate } from '@/lib/format'
import { members, postedLabel, type FeedPost } from '@/lib/membersApi'
import { Carousel } from '../content/Carousel'
import { Badge, useToast } from '../ui'
import { Avatar } from './Avatar'
import { ConfirmDialog } from './ConfirmDialog'
import { EditPostDialog } from './EditPostDialog'
import { OverflowMenu, type MenuItem } from './OverflowMenu'
import { ReportDialog } from './ReportDialog'
import { SensitiveBlur } from './SensitiveBlur'

const STATE_LABELS: Record<string, string> = {
  pending: 'Waiting for review',
  processing: 'Processing',
  hidden_by_report: 'Hidden while we review a report',
  removed: 'Removed',
}

interface PostCardProps {
  post: FeedPost
  onChange: (post: FeedPost | null) => void
  linkToDetail?: boolean
}

type Dialog = 'report' | 'edit' | 'delete' | 'block' | null

export function PostCard({ post, onChange, linkToDetail = true }: PostCardProps) {
  const toast = useToast()
  const [expanded, setExpanded] = useState(false)
  const [dialog, setDialog] = useState<Dialog>(null)
  const [busy, setBusy] = useState(false)
  const label = postedLabel(post.posted, relativeDate)
  const stateLabel =
    post.state && post.state !== 'published'
      ? post.state === 'processing' && post.in_review
        ? 'Processing, then waiting for review'
        : STATE_LABELS[post.state]
      : null
  const long = post.caption_html.length > 240 || (post.caption_html.match(/<br>/g)?.length ?? 0) > 3

  async function toggleLike() {
    const optimistic = {
      ...post,
      liked_by_me: !post.liked_by_me,
      like_count: post.like_count === null ? null : post.like_count + (post.liked_by_me ? -1 : 1),
    }
    onChange(optimistic)
    try {
      onChange(await (post.liked_by_me ? members.unlike(post.id) : members.like(post.id)))
    } catch {
      onChange(post)
      toast.show({ tone: 'error', title: 'That did not work', message: 'Please try again.' })
    }
  }

  async function run(action: () => Promise<unknown>, success: string, removeFromList: boolean) {
    setBusy(true)
    try {
      await action()
      setDialog(null)
      toast.show({ tone: 'success', title: success })
      if (removeFromList) onChange(null)
    } catch {
      toast.show({ tone: 'error', title: 'That did not work', message: 'Please try again.' })
    } finally {
      setBusy(false)
    }
  }

  const menu: MenuItem[] = post.is_own
    ? [
        { label: 'Edit', onSelect: () => setDialog('edit') },
        { label: 'Delete', onSelect: () => setDialog('delete'), danger: true },
      ]
    : [
        { label: 'Report', onSelect: () => setDialog('report') },
        { label: `Mute ${post.author.handle}`, onSelect: () => void run(() => members.relate(post.author.handle, 'mute'), `${post.author.handle} is muted`, true) },
        { label: `Block ${post.author.handle}`, onSelect: () => setDialog('block'), danger: true },
      ]

  const profileLink = `/members/u/${encodeURIComponent(post.author.handle)}`
  const commentsLabel = post.comment_count > 0 ? `${post.comment_count} ${post.comment_count === 1 ? 'comment' : 'comments'}` : 'Comment'

  return (
    <article className="relative border-b border-border pb-4" aria-label={`Post by ${post.author.handle}`}>
      <header className="flex items-center gap-3 px-1 pb-3">
        <Link to={profileLink} className="flex min-w-0 flex-1 items-center gap-3">
          <Avatar member={post.author} />
          <span className="flex min-w-0 items-baseline gap-1 text-sm">
            <span className="truncate font-semibold text-fg">{post.author.handle}</span>
            <span aria-hidden="true" className="text-fg-muted">
              ·
            </span>
            <span className="shrink-0 text-fg-muted">
              {post.posted.at ? <time dateTime={post.posted.at}>{label}</time> : label}
              {post.edited && ' · edited'}
            </span>
          </span>
        </Link>
        <OverflowMenu items={menu} label="Post options" />
      </header>

      {stateLabel && (
        <p className="mb-3 flex items-center gap-2 rounded-lg bg-primary-deep px-3 py-2 text-sm text-fg">
          <Hourglass aria-hidden="true" className="size-4" />
          {stateLabel}
        </p>
      )}

      {post.images.length > 0 && (
        <div>
          <SensitiveBlur blurred={post.blur}>
            <Carousel images={post.images} label={`Images in ${post.author.handle}'s post`} protect />
          </SensitiveBlur>
        </div>
      )}
      {post.images.length === 0 && post.state === 'processing' && (
        <div className="aspect-square animate-pulse rounded-xl bg-surface-sunken" />
      )}

      <div className="-ml-2 flex items-center pt-1">
        <button
          type="button"
          onClick={toggleLike}
          aria-pressed={post.liked_by_me}
          className="inline-flex size-11 items-center justify-center rounded-full text-fg hover:text-fg-muted"
        >
          <Heart aria-hidden="true" className={cn('size-6', post.liked_by_me && 'fill-rose text-rose')} strokeWidth={1.9} />
          <span className="sr-only">{post.liked_by_me ? 'Liked' : 'Like'}</span>
        </button>
        {post.comments_enabled ? (
          linkToDetail ? (
            <Link to={`/members/p/${post.id}`} className="inline-flex size-11 items-center justify-center rounded-full text-fg hover:text-fg-muted">
              <MessageCircle aria-hidden="true" className="size-6 -scale-x-100" strokeWidth={1.9} />
              <span className="sr-only">{commentsLabel}</span>
            </Link>
          ) : null
        ) : (
          <Badge className="ml-2">Comments off</Badge>
        )}
      </div>

      {/* Only the author is sent a count; everyone else sees none. */}
      {post.like_count !== null && (
        <p className="px-1 text-sm font-semibold text-fg">{`${post.like_count} ${post.like_count === 1 ? 'like' : 'likes'}`}</p>
      )}

      {post.caption_html && (
        <div className="px-1 pt-1 text-sm">
          <div className={cn('leading-relaxed text-fg', !expanded && long && 'line-clamp-2')}>
            <Link to={profileLink} className="font-semibold text-fg">
              {post.author.handle}
            </Link>{' '}
            <span
              className="[&_a]:text-accent [&_a]:underline"
              // Sanitised on the server: only <br> and https links survive.
              dangerouslySetInnerHTML={{ __html: post.caption_html }}
            />
          </div>
          {long && (
            <button type="button" onClick={() => setExpanded((value) => !value)} className="text-fg-muted hover:text-fg">
              {expanded ? 'less' : 'more'}
            </button>
          )}
        </div>
      )}

      {post.comments_enabled && linkToDetail && post.comment_count > 0 && (
        <Link to={`/members/p/${post.id}`} className="mt-1 block px-1 text-sm text-fg-muted hover:text-fg">
          View {post.comment_count === 1 ? 'the comment' : `all ${post.comment_count} comments`}
        </Link>
      )}

      <ReportDialog open={dialog === 'report'} onClose={() => setDialog(null)} targetType="post" targetId={post.id} />
      <EditPostDialog open={dialog === 'edit'} post={post} onClose={() => setDialog(null)} onSaved={(next) => { onChange(next); setDialog(null) }} />
      <ConfirmDialog
        open={dialog === 'delete'}
        title="Delete this post?"
        confirmLabel="Delete for good"
        busy={busy}
        onClose={() => setDialog(null)}
        onConfirm={() => void run(() => members.deletePost(post.id), 'Post deleted', true)}
      >
        <p>The post, its photos and its comments are deleted permanently.</p>
      </ConfirmDialog>
      <ConfirmDialog
        open={dialog === 'block'}
        title={`Block ${post.author.handle}?`}
        confirmLabel="Block"
        busy={busy}
        onClose={() => setDialog(null)}
        onConfirm={() => void run(() => members.relate(post.author.handle, 'block'), `${post.author.handle} is blocked`, true)}
      >
        <p>You will not see each other's posts, comments or profiles. They are not told.</p>
        <p>You can unblock them later from your profile.</p>
      </ConfirmDialog>
    </article>
  )
}

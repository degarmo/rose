import { Heart, Hourglass, MessageCircle } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { cn } from '@/lib/cn'
import { relativeDate } from '@/lib/format'
import { members, postedLabel, type FeedPost } from '@/lib/membersApi'
import { Carousel } from '../content/Carousel'
import { Badge, Card, useToast } from '../ui'
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

  return (
    <Card as="article" className="overflow-visible" aria-label={`Post by ${post.author.handle}`}>
      <header className="flex items-center gap-3 px-4 pb-3 pt-4">
        <Link to={`/members/u/${encodeURIComponent(post.author.handle)}`} className="flex min-w-0 flex-1 items-center gap-3">
          <Avatar member={post.author} />
          <span className="min-w-0">
            <span className="block truncate font-medium text-fg">{post.author.handle}</span>
            <span className="block text-xs text-fg-subtle">
              {post.posted.at ? <time dateTime={post.posted.at}>{label}</time> : label}
              {post.edited && ' · edited'}
            </span>
          </span>
        </Link>
        <OverflowMenu items={menu} label="Post options" />
      </header>

      {stateLabel && (
        <p className="mx-4 mb-3 flex items-center gap-2 rounded-lg border border-highlight/30 bg-surface-raised px-3 py-2 text-sm text-fg-muted">
          <Hourglass aria-hidden="true" className="size-4 text-highlight" />
          {stateLabel}
        </p>
      )}

      {post.images.length > 0 && (
        <div className="px-2">
          <SensitiveBlur blurred={post.blur}>
            <Carousel images={post.images} label={`Images in ${post.author.handle}'s post`} protect />
          </SensitiveBlur>
        </div>
      )}
      {post.images.length === 0 && post.state === 'processing' && (
        <div className="mx-2 aspect-square animate-pulse rounded-xl bg-surface-raised" />
      )}

      {post.caption_html && (
        <div className="px-4 pt-3">
          <div
            className={cn(
              'leading-relaxed text-fg-muted [&_a]:text-accent [&_a]:underline [&_a]:underline-offset-4',
              !expanded && long && 'line-clamp-3',
            )}
            // Sanitised on the server: only <br> and https links survive.
            dangerouslySetInnerHTML={{ __html: post.caption_html }}
          />
          {long && (
            <button type="button" onClick={() => setExpanded((value) => !value)} className="mt-1 text-sm text-fg-subtle hover:text-fg">
              {expanded ? 'Less' : 'More'}
            </button>
          )}
        </div>
      )}

      <footer className="flex items-center gap-2 px-2 pb-2 pt-2">
        <button
          type="button"
          onClick={toggleLike}
          aria-pressed={post.liked_by_me}
          className="inline-flex min-h-11 items-center gap-2 rounded-full px-3 text-sm text-fg-muted hover:text-fg"
        >
          <Heart aria-hidden="true" className={cn('size-5', post.liked_by_me && 'fill-rose text-rose')} />
          <span className={cn(post.like_count === null && 'sr-only')}>
            {post.like_count === null ? (post.liked_by_me ? 'Liked' : 'Like') : `${post.like_count} ${post.like_count === 1 ? 'like' : 'likes'}`}
          </span>
        </button>
        {post.comments_enabled ? (
          linkToDetail ? (
            <Link to={`/members/p/${post.id}`} className="inline-flex min-h-11 items-center gap-2 rounded-full px-3 text-sm text-fg-muted hover:text-fg">
              <MessageCircle aria-hidden="true" className="size-5" />
              {post.comment_count > 0 ? `${post.comment_count} ${post.comment_count === 1 ? 'comment' : 'comments'}` : 'Comment'}
            </Link>
          ) : null
        ) : (
          <Badge>Comments off</Badge>
        )}
      </footer>

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
    </Card>
  )
}

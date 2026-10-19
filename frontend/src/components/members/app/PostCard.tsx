import { Bookmark, Ellipsis, Heart, Hourglass, MessageCircle } from 'lucide-react'
import { useId, useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router'
import { cn } from '@/lib/cn'
import { isExternalUrl, relativeDate } from '@/lib/format'
import { members, postedLabel, postedShort, type ClubPost, type FeedComment, type FeedPost, type Posted } from '@/lib/membersApi'
import { useToast } from '../../ui'
import { Avatar } from '../Avatar'
import { SensitiveBlur } from '../SensitiveBlur'
import { useMembers } from '../membersContext'
import { MediaCarousel } from './MediaCarousel'
import { isClub, profilePath } from './postUtils'
import { RoseMark } from './primitives'
import { ICON } from './ui'
import { useLatestPost, usePostActions } from './usePost'

const COMMENT_LIMIT = 500

const STATE_LABELS: Record<string, string> = {
  pending: 'Waiting for review',
  processing: 'Processing',
  hidden_by_report: 'Hidden while we review a report',
  removed: 'Removed',
}

function When({ posted, short = false, className }: { posted: Posted; short?: boolean; className?: string }) {
  const label = short ? postedShort(posted) : postedLabel(posted, relativeDate)
  return posted.at ? (
    <time dateTime={posted.at} className={className}>
      {label}
    </time>
  ) : (
    <span className={className}>{label}</span>
  )
}

/** A link to a website page (router) or an outside https address. */
export function SiteLink({ to, className, children }: { to: string; className?: string; children: ReactNode }) {
  if (isExternalUrl(to)) {
    return (
      <a href={to} rel="noopener noreferrer" className={className}>
        {children}
      </a>
    )
  }
  return (
    <Link to={to} className={className}>
      {children}
    </Link>
  )
}

// 1. Header

/** Design: 56px tall, 16px side padding, 12px gap; a 32px avatar, the handle (600) and "• 2h". */
export function PostHeader({ post, onMore, className }: { post: FeedPost | ClubPost; onMore?: () => void; className?: string }) {
  const club = isClub(post)
  const name = (
    <span className="flex min-w-0 items-center gap-1">
      <span className={cn('truncate font-semibold text-fg', club && 'font-serif text-[0.9375rem] font-medium')}>{post.author.handle}</span>
      <span className="shrink-0 text-fg-muted">
        <span aria-hidden="true">• </span>
        <When posted={post.posted} short />
      </span>
    </span>
  )
  return (
    <header className={cn('flex h-14 items-center gap-3 px-4', className)}>
      {club ? (
        <span className="flex min-w-0 flex-1 items-center gap-3">
          <RoseMark className="size-8 text-sm" />
          {name}
        </span>
      ) : (
        <Link to={profilePath(post.author.handle)} className="flex min-w-0 flex-1 items-center gap-3">
          <Avatar member={post.author} size="sm" />
          {name}
        </Link>
      )}
      {onMore && (
        <button type="button" onClick={onMore} className="-mr-2 inline-flex size-10 items-center justify-center text-fg hover:text-fg-muted">
          <Ellipsis aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} />
          <span className="sr-only">Post options</span>
        </button>
      )}
    </header>
  )
}

// 3. Action row

export function ActionRow({
  post,
  onLike,
  onSave,
  onComment,
}: {
  post: FeedPost
  onLike: () => void
  onSave: () => void
  /** Opens the post (feed) or focuses the comment box (post detail). */
  onComment?: () => void
}) {
  return (
    <div className="-mx-2 flex h-11 items-center">
      <button
        type="button"
        onClick={onLike}
        aria-pressed={post.liked_by_me}
        className="inline-flex size-10 items-center justify-center text-fg hover:text-fg-muted"
      >
        <Heart
          key={String(post.liked_by_me)}
          aria-hidden="true"
          size={ICON.size}
          strokeWidth={ICON.stroke}
          className={cn(post.liked_by_me && 'animate-like-pop fill-primary text-primary')}
        />
        <span className="sr-only">{post.liked_by_me ? 'Liked' : 'Like'}</span>
      </button>
      {post.comments_enabled && onComment && (
        <button type="button" onClick={onComment} className="inline-flex size-10 items-center justify-center text-fg hover:text-fg-muted">
          <MessageCircle aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} className="-scale-x-100" />
          <span className="sr-only">Comment</span>
        </button>
      )}
      <button
        type="button"
        onClick={onSave}
        aria-pressed={post.saved_by_me}
        className="ml-auto inline-flex size-10 items-center justify-center text-fg hover:text-fg-muted"
      >
        <Bookmark aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} className={cn(post.saved_by_me && 'fill-fg')} />
        <span className="sr-only">{post.saved_by_me ? 'Saved' : 'Save'}</span>
      </button>
    </div>
  )
}

// 4. Likes line

/** The author sees how many; everyone else sees only their own like. Never who liked it. */
export function LikesLine({ post }: { post: FeedPost }) {
  if (post.like_count !== null) {
    return <p className="font-semibold text-fg">{`${post.like_count} ${post.like_count === 1 ? 'like' : 'likes'}`}</p>
  }
  if (post.liked_by_me) return <p className="font-semibold text-fg">Liked by you</p>
  return null
}

// 5. Caption

export function Caption({ post, clamp = true }: { post: FeedPost | ClubPost; clamp?: boolean }) {
  const [expanded, setExpanded] = useState(false)
  if (!post.caption_html) return null
  const long = post.caption_html.length > 125 || (post.caption_html.match(/<br>/g)?.length ?? 0) > 1
  const cut = clamp && long && !expanded
  return (
    <div>
      <p className={cn('break-words text-fg', cut && 'line-clamp-2')}>
        {isClub(post) ? (
          <span className="font-semibold">{post.author.handle}</span>
        ) : (
          <Link to={profilePath(post.author.handle)} className="font-semibold text-fg">
            {post.author.handle}
          </Link>
        )}{' '}
        <span
          className="[&_a]:text-link [&_a]:underline"
          // Sanitised on the server: only <br> and https links survive.
          dangerouslySetInnerHTML={{ __html: post.caption_html }}
        />
      </p>
      {cut && (
        <button type="button" onClick={() => setExpanded(true)} className="min-h-6 text-fg-muted hover:text-fg">
          more
        </button>
      )}
    </div>
  )
}

function CommentLine({ comment }: { comment: FeedComment }) {
  return (
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
  )
}

// 8. Comment field

export function CommentForm({
  post,
  onCommented,
  inputId,
  className,
}: {
  post: FeedPost
  onCommented: (comment: FeedComment) => void
  inputId?: string
  className?: string
}) {
  const fallbackId = useId()
  const id = inputId ?? fallbackId
  const toast = useToast()
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const text = body.trim()

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!text || busy) return
    setBusy(true)
    try {
      onCommented(await members.addComment(post.id, text))
      setBody('')
    } catch (error) {
      toast.show({ tone: 'error', title: 'Your comment was not posted', message: error instanceof Error ? error.message : undefined })
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className={cn('flex items-center gap-2', className)} aria-label="Add a comment">
      <label htmlFor={id} className="sr-only">
        Add a comment
      </label>
      <input
        id={id}
        value={body}
        maxLength={COMMENT_LIMIT}
        onChange={(event) => setBody(event.target.value)}
        placeholder="Add a comment…"
        autoComplete="off"
        className="min-w-0 flex-1 bg-transparent py-1 text-sm text-fg placeholder:text-fg-muted focus:outline-none"
      />
      <button
        type="submit"
        disabled={!text || busy}
        className={cn('text-sm font-semibold transition-colors duration-150', text ? 'text-link hover:text-primary-hover' : 'cursor-default text-link/50')}
      >
        Post
      </button>
    </form>
  )
}

function StateNote({ post }: { post: FeedPost }) {
  const label =
    post.state && post.state !== 'published'
      ? post.state === 'processing' && post.in_review
        ? 'Processing, then waiting for review'
        : STATE_LABELS[post.state]
      : null
  if (!label) return null
  return (
    <p className="mx-4 mb-3 flex items-center gap-2 rounded-app bg-surface px-3 py-2 text-fg">
      <Hourglass aria-hidden="true" strokeWidth={ICON.stroke} className="size-4" />
      {label}
    </p>
  )
}

/** The timestamp under a post (design: 10px caps with .2px tracking). */
function Stamp({ posted }: { posted: Posted }) {
  return <When posted={posted} className="block pt-0.5 text-[0.625rem] uppercase leading-[18px] tracking-[0.2px] text-fg-muted" />
}

function MemberPostCard({ post, onOpen, priority }: { post: FeedPost; onOpen: () => void; priority: boolean }) {
  const { patchPost } = useMembers()
  const { toggleLike, likeOnce, toggleSave, openSheet, dialogs } = usePostActions(post)
  const canComment = post.comments_enabled && (post.state === null || post.state === 'published')

  return (
    <article className="border-b border-border pb-3" aria-label={`Post by ${post.author.handle}`}>
      <PostHeader post={post} onMore={openSheet} />
      <StateNote post={post} />
      {post.images.length > 0 && (
        <SensitiveBlur blurred={post.blur}>
          <MediaCarousel images={post.images} label={`Images in ${post.author.handle}'s post`} protect onDoubleTap={likeOnce} priority={priority} dotsBelow />
        </SensitiveBlur>
      )}
      {post.images.length === 0 && post.state === 'processing' && <div className="wash-rose aspect-square animate-pulse" />}

      <div className="px-4 pt-1.5">
        <ActionRow post={post} onLike={() => void toggleLike()} onSave={() => void toggleSave()} onComment={onOpen} />
      </div>
      <div className="flex flex-col gap-1 px-4">
        <LikesLine post={post} />
        <Caption post={post} />
        {post.comment_count > 0 && (
          <button type="button" onClick={onOpen} className="flex min-h-6 items-center self-start text-fg-muted hover:text-fg">
            {post.comment_count === 1 ? 'View 1 comment' : `View all ${post.comment_count} comments`}
          </button>
        )}
        {post.recent_comments.map((comment) => (
          <CommentLine key={comment.id} comment={comment} />
        ))}
        <Stamp posted={post.posted} />
        {canComment && (
          <CommentForm
            post={post}
            className="pt-1.5"
            onCommented={(comment) =>
              patchPost(post, (current) => ({ ...current, comment_count: current.comment_count + 1, recent_comments: [...current.recent_comments, comment].slice(-2) }))
            }
          />
        )}
      </div>
      {dialogs}
    </article>
  )
}

/**
 * A journal post from the club, shown as "Rose". It lives on the website, so there are no
 * likes, comments or saves: its action row is the way there.
 */
function ClubPostCard({ post, priority }: { post: ClubPost; priority: boolean }) {
  return (
    <article className="border-b border-border pb-3" aria-label={`Post by ${post.author.handle}`}>
      <PostHeader post={post} />
      {post.images.length > 0 && <MediaCarousel images={post.images} label={`Images in ${post.author.handle}'s post`} protect={false} priority={priority} dotsBelow />}
      <div className="flex h-11 items-center px-4 pt-1.5">
        <SiteLink to={post.link.url} className="font-semibold text-link hover:text-primary-hover">
          {post.link.label} <span aria-hidden="true">→</span>
        </SiteLink>
      </div>
      <div className="flex flex-col gap-1 px-4">
        <Caption post={post} />
        <Stamp posted={post.posted} />
      </div>
    </article>
  )
}

interface PostCardProps {
  post: FeedPost | ClubPost
  /** Ids of the list this card is in, so the post view can step through them with the arrow keys. */
  listIds?: string[]
  /** The first post in a feed: its first photo is fetched before anything else. */
  priority?: boolean
}

function LiveMemberPostCard({ post, listIds, priority }: { post: FeedPost; listIds?: string[]; priority: boolean }) {
  const { openPost } = useMembers()
  const latest = useLatestPost(post)
  if (!latest) return null
  return <MemberPostCard post={latest} onOpen={() => openPost(post.id, listIds)} priority={priority} />
}

/** One post in a feed, for member and club posts alike. */
export function PostCard({ post, listIds, priority = false }: PostCardProps) {
  if (isClub(post)) return <ClubPostCard post={post} priority={priority} />
  return <LiveMemberPostCard post={post} listIds={listIds} priority={priority} />
}

import { Copy } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { cn } from '@/lib/cn'
import type { FeedPost } from '@/lib/membersApi'
import { useCursorList, type CursorPage } from '@/lib/useCursorList'
import { useMembers } from '../membersContext'
import { useLatestPost } from './usePost'
import { IgButton } from './primitives'

function Tile({ post, ids }: { post: FeedPost; ids: string[] }) {
  const { openPost } = useMembers()
  const latest = useLatestPost(post)
  if (!latest) return null
  const cover = latest.images[0]
  const label = latest.posted.at ? `Post from ${new Date(latest.posted.at).toLocaleDateString('en-US')}` : `Post from ${latest.posted.month}`
  return (
    <li>
      <Link
        to={`/members/p/${encodeURIComponent(latest.id)}`}
        onClick={(event) => {
          event.preventDefault()
          openPost(latest.id, ids)
        }}
        onContextMenu={(event) => event.preventDefault()}
        className="group relative block aspect-[3/4] overflow-hidden bg-surface"
        aria-label={label}
      >
        {cover ? (
          <img
            src={cover.url}
            alt=""
            loading="lazy"
            draggable={false}
            className={cn('size-full select-none object-cover [-webkit-touch-callout:none]', latest.blur && 'scale-110 blur-xl')}
          />
        ) : (
          <span
            className="absolute inset-0 line-clamp-6 p-3 text-xs leading-snug text-fg"
            // Sanitised on the server.
            dangerouslySetInnerHTML={{ __html: latest.caption_html }}
          />
        )}
        {latest.images.length > 1 && <Copy aria-hidden="true" className="absolute right-2 top-2 size-5 text-white drop-shadow" strokeWidth={2} />}
        {/* A soft overlay on hover with a mouse; never counts. */}
        <span aria-hidden="true" className="absolute inset-0 bg-black/0 transition-colors duration-150 md:group-hover:bg-black/25" />
      </Link>
    </li>
  )
}

interface PostGridProps {
  loader: (cursor: string | null) => Promise<CursorPage<FeedPost>>
  listKey: string
  empty: ReactNode
}

/** Three columns of 3:4 portrait tiles with 2px gaps; edge to edge on phones. */
export function PostGrid({ loader, listKey, empty }: PostGridProps) {
  const { base, status, loadMore, retry, bindSentinel } = useCursorList(loader, listKey)
  const ids = base.map((post) => post.id)
  return (
    <div>
      <ul className="grid grid-cols-3 gap-0.5">
        {base.map((post) => (
          <Tile key={post.id} post={post} ids={ids} />
        ))}
      </ul>
      <div ref={bindSentinel} className="mt-6 flex justify-center" aria-live="polite">
        {status === 'loading' && <LoadingState label="Loading posts" />}
        {status === 'error' && <ErrorState title="Posts did not load" onRetry={retry} />}
        {status === 'idle' && (
          <IgButton variant="secondary" onClick={() => void loadMore()}>
            Load more
          </IgButton>
        )}
        {status === 'done' && base.length === 0 && empty}
      </div>
    </div>
  )
}

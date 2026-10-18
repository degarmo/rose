import { Link } from 'react-router'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import type { FeedPost } from '@/lib/membersApi'
import { applyEdits, useCursorList, type CursorPage } from '@/lib/useCursorList'
import { Button } from '../ui'
import { PostCard } from './PostCard'

interface PostListProps {
  loader: (cursor: string | null) => Promise<CursorPage<FeedPost>>
  listKey: string
  empty: { title: string; message: string }
}

/** Single-column cards with infinite scroll and a visible "Load more" fallback. */
export function PostList({ loader, listKey, empty }: PostListProps) {
  const { base, edits, status, loadMore, retry, bindSentinel, update } = useCursorList(loader, listKey)
  const posts = applyEdits(base, edits)

  return (
    <div>
      <ul className="flex flex-col gap-5">
        {posts.map((post) => (
          <li key={post.id}>
            <PostCard post={post} onChange={(next) => update(post.id, next)} />
          </li>
        ))}
      </ul>
      <div ref={bindSentinel} className="mt-8 flex flex-col items-center gap-4" aria-live="polite">
        {status === 'loading' && <LoadingState label="Loading posts" />}
        {status === 'error' && <ErrorState title="Posts did not load" onRetry={retry} />}
        {status === 'idle' && (
          <Button variant="ghost" onClick={() => void loadMore()}>
            Load more
          </Button>
        )}
        {status === 'done' && posts.length === 0 && (
          <div className="w-full">
            <EmptyState title={empty.title} message={empty.message} />
            <p className="mt-4 text-center text-sm text-fg-muted">
              New here? Read the{' '}
              <Link to="/members/join-feed?guidelines=1" className="text-accent underline underline-offset-4">
                community guidelines
              </Link>{' '}
              or find people in the{' '}
              <Link to="/members/directory" className="text-accent underline underline-offset-4">
                directory
              </Link>
              .
            </p>
          </div>
        )}
        {status === 'done' && posts.length > 0 && <p className="text-sm text-fg-subtle">You are all caught up.</p>}
      </div>
    </div>
  )
}
